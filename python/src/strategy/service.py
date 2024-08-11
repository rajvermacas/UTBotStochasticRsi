# List of profit indicator columns
# Profit columns by default are cumulated till date
# profit_columns = [
#     'profit_atrBuySignal',
#     'profit_rsiBuySignal',
#     'profit_stochasticBuySignal',
#     'profit_atrBuySignal_rsiBuySignal',
#     'profit_atrBuySignal_stochasticBuySignal',
#     'profit_rsiBuySignal_stochasticBuySignal',
#     'profit_atrBuySignal_rsiBuySignal_stochasticBuySignal'
# ]

# # Corresponding signal columns
# signal_columns = [
#     ['atrBuySignal'],
#     ['rsiBuySignal'],
#     ['stochasticBuySignal'],
#     ['atrBuySignal', 'rsiBuySignal'],
#     ['atrBuySignal', 'stochasticBuySignal'],
#     ['rsiBuySignal', 'stochasticBuySignal'],
#     ['atrBuySignal', 'rsiBuySignal', 'stochasticBuySignal']
# ]
from functools import partial
import os
import traceback
import builtins
import pandas as pd
import re
import datetime

from indicator.service import populate_profit_cols, get_profit_column_name
from lib.models import Transaction
from lib import params as app_params
from lib.models import StrategyStatBuilder


def find_best_transactions(args, row):
    """
    Find the best transactions based on the input arguments and the current row.

    Parameters:
    - args: Tuple containing the current strategy state, buy column combinations, and ticker name.
    - row: The current row of data.

    Returns:
    - None
    - But updates the current strategy state with the best transactions.
    """
    curr_strategy_state, buy_cols_combinations, ticker_name = args
    sell_column = app_params.ATR_SELL_COLUMN

    max_profit = None
    best_signal_column_combination = None

    # Only take trade when not in trade already
    if not curr_strategy_state['open_position']:
        for signal_cols in buy_cols_combinations:
            profit_col = get_profit_column_name(signal_cols)

            if max_profit is None or \
                (row[profit_col] is not None and row[profit_col] > max_profit):
                # Enter long position
                max_profit = row[profit_col]
                best_signal_column_combination = signal_cols
                curr_strategy_state['buy_columns'] = signal_cols

        # Check if the most profitable strategy is giving a buy signal
        if best_signal_column_combination and all(
            row[signal_col] for signal_col in best_signal_column_combination
        ):
            # Open position
            curr_strategy_state['open_position'] = True

            buy_quantity = app_params.CAPITAL/row['Close']
            curr_strategy_state['trade_history'].append(
                Transaction(ticker_name, buy_quantity, row['Close'], row.name, curr_strategy_state['buy_columns'])
            )

    # If there is a sell signal, book profit
    if curr_strategy_state['open_position'] and row[sell_column]:
        transaction = curr_strategy_state['trade_history'][-1]
        transaction.end(row['Close'], row.name)
        curr_strategy_state['open_position'] = False

    
def summarise_transactions(transactions: list, 
                           backtest_start_date: str, 
                           backtest_end_date: str):
    
    wins = 0
    losses = 0
    entries = 0
    exits = 0
    profit_and_loss = 0
    profit_perc = 0

    # Split the period from backtest_start_date to backtest_end_date into n sections
    checkpoint_dates = [pd.to_datetime(backtest_start_date) + pd.Timedelta(
            days=int(
                (pd.to_datetime(backtest_end_date) - pd.to_datetime(backtest_start_date)).days * i / app_params.PROFIT_INTERVALS
            )
        ) for i in range(1, app_params.PROFIT_INTERVALS)
    ]
    checkpoint_dates.append(pd.to_datetime(backtest_end_date))

    profit_per_interval = [0] * app_params.PROFIT_INTERVALS
    wins_per_interval = [0] * app_params.PROFIT_INTERVALS
    losses_per_interval = [0] * app_params.PROFIT_INTERVALS
    entries_per_interval = [0] * app_params.PROFIT_INTERVALS
    exits_per_interval = [0] * app_params.PROFIT_INTERVALS

    # Make sure the transactions are sorted on its sell_date
    transactions.sort(
        key=lambda transaction: transaction.sell_date if transaction.sell_date else pd.Timestamp.max
    )

    # Populate metrics per interval
    for transaction in transactions:
        if not transaction.is_active():
            if transaction.sell_price > transaction.buy_price:
                wins += 1
            else:
                losses += 1

            entries += 1
            exits += 1
            profit_perc += transaction.profit_perc

            for i in range(app_params.PROFIT_INTERVALS):
                if pd.to_datetime(transaction.sell_date) <= checkpoint_dates[i]:
                    profit_per_interval[i] = round(profit_per_interval[i] + transaction.profit_perc, 2)
                    entries_per_interval[i] += 1
                    exits_per_interval[i] += 1
                    if transaction.sell_price > transaction.buy_price:
                        wins_per_interval[i] += 1
                    else:
                        losses_per_interval[i] += 1
                    break

    winrate = 0
    if entries > 0:
        winrate = round((wins / entries) * 100, 2)

    profit_and_loss = 0
    if exits > 0:
        profit_and_loss = round((wins - losses) / exits, 2)

    result = {
        'Wins': wins,
        'Losses': losses,
        'Entries': entries,
        'Exits': exits,
        'Winrate': winrate,
        'Profit/StockGrowth': profit_and_loss,
        'Profit': round(profit_perc, 2),
    }

    for i in range(app_params.PROFIT_INTERVALS):
        result[f'CheckpointProfit{i+1}'] = profit_per_interval[i]
        result[f'CheckpointWins{i+1}'] = wins_per_interval[i]
        result[f'CheckpointLosses{i+1}'] = losses_per_interval[i]
        result[f'CheckpointEntries{i+1}'] = entries_per_interval[i]
        result[f'CheckpointExits{i+1}'] = exits_per_interval[i]
        result[f'CheckpointWinrate{i+1}'] = round((wins_per_interval[i] / entries_per_interval[i] * 100), 2) if entries_per_interval[i] > 0 else None

    return result

def get_best_strategy_stats(args):
    """
    This function calculates the best strategy statistics for a given stock.
    
    Parameters:
    ticker_name (str): The name of the stock.
    stock_growth (float): The growth of the stock.
    df_ticker (pandas.DataFrame): A DataFrame containing the stock's data.
    sell_column (str): The column name for selling signals.
    buy_columns_combinations (list): A list of combinations of column names for buying signals.
    
    Returns:
    dict: A dictionary containing the best strategy statistics, including the stock's name, date, growth, wins, losses, entries, exits, winrate, profit, and profit/stock growth ratio.
    """
    try:
        ticker_name, stock_growth, df_ticker, sell_column, buy_columns_combinations, backtest_start_date, backtest_end_date = args        

        df_profit_cols = populate_profit_cols(df_ticker, ticker_name, buy_columns_combinations, sell_column)

        # Prepare temporary strategy state for function find_best_strategy_stat
        curr_strategy_state = {
            'open_position': False,
            'buy_columns': None,
            'trade_history': [],
        }
        
        args = (curr_strategy_state, buy_columns_combinations, ticker_name)
        df_profit_cols.apply(partial(find_best_transactions, args), axis=1)

        strategy_stat = StrategyStatBuilder.build(ticker_name, df_ticker.index[-1], stock_growth)

        best_strategy_stat = summarise_transactions(
            curr_strategy_state['trade_history'],
            backtest_start_date,
            backtest_end_date
        )
        strategy_stat.update(best_strategy_stat)

        if strategy_stat['Stock Growth'] < 0 and strategy_stat['Profit'] < 0:
            strategy_stat['Profit/StockGrowth'] = -round(strategy_stat['Profit'] / strategy_stat['Stock Growth'], 2)

        else:
            strategy_stat['Profit/StockGrowth'] = round(strategy_stat['Profit'] / strategy_stat['Stock Growth'], 2)
        
        # print(f"Stock={ticker_name} Trade history={[str(transaction) for transaction in strategy_stat['TradeHistory']]}")
        builtins.logging.info(f"Stock={ticker_name} Trade history={[str(transaction) for transaction in curr_strategy_state['trade_history']]}")

        if os.environ.get('EXECUTION_MODE') == app_params.EXECUTION_MODE_TEST:
            csv_path = os.path.join(os.getenv("OUTPUT_DIR"), f"test_{ticker_name}_transactions.csv")
            df_transactions = pd.DataFrame([transaction.to_dict() for transaction in curr_strategy_state['trade_history']])
            df_transactions.to_csv(csv_path, index=False)
            print(f"CSV created: Transactions of Stock={ticker_name} saved at path={os.path.join(os.getenv('OUTPUT_DIR'), f'test_{ticker_name}_transactions.csv')}")

            csv_path = os.path.join(os.getenv("OUTPUT_DIR"), f"test_{ticker_name}_profit.csv")
            df_profit_cols.to_csv(csv_path)
            print(f"CSV created: Profit columns of Stock={ticker_name} saved at path={csv_path}")

        return strategy_stat, curr_strategy_state['trade_history']

    except Exception as fault:
        print(f"Error occured while getting best strategy stats. error={fault}")
        traceback.print_exc()

def is_favourite_stock(strategy_stat: dict, ticker_name: str, \
                       manual_favourite_stocks: set) -> bool:
    
    # Below are the Checkpoint columns
    # CheckpointProfit\d+
    # CheckpointWins\d+
    # CheckpointLosses\d+
    # CheckpointEntries\d+
    # CheckpointExits\d+
    # CheckpointWinrate\d+
    
    pattern_profit = r'CheckpointProfit\d+'
    pattern_winrate = r'CheckpointWinrate\d+'

    checkpoint_profit_cols = [key for key in strategy_stat.keys() if re.match(pattern_profit, key)]
    checkpoint_profit_cols.sort()

    checkpoint_winrate_cols = [key for key in strategy_stat.keys() if re.match(pattern_winrate, key)]
    checkpoint_winrate_cols.sort()

    checkpoint_pass = True
    if checkpoint_profit_cols and checkpoint_winrate_cols:
        # Find all the values in CheckpointProfit* keys that are greater than 30 if there was a trade taken in that interval
        # If there is no trade taken in the interval then consider it as pass
        for profit_col in checkpoint_profit_cols :
            checkpoint_pass &= strategy_stat[profit_col] > app_params.CHECKPOINT_PROFIT_PERC_THRESHOLD
    
    manual_favourite_stocks = set(map(str.lower, manual_favourite_stocks))
    return (ticker_name.lower() in manual_favourite_stocks) \
        or (
            checkpoint_pass \
            and (strategy_stat['Profit'] >= 100) \
            and (strategy_stat['Winrate'] >= 60)
        )
