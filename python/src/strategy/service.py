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
    curr_strategy_state, buy_cols_combinations, ticker_name = args
    sell_column = app_params.ATR_SELL_COLUMN

    max_profit = 0
    best_signal_column_combination = None

    # Only take trade when not in trade already
    if not curr_strategy_state['open_position']:
        for signal_cols in buy_cols_combinations:
            profit_col = get_profit_column_name(signal_cols)

            if row[profit_col] and row[profit_col] > max_profit:
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

    # If there is a sell siganl, book profit
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
        key=lambda transaction: transaction.sell_date if transaction.sell_date else pd.Timestamp.min
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
        result[f'CheckpointWinrate{i+1}'] = round((wins_per_interval[i] / entries_per_interval[i] * 100), 2) if entries_per_interval[i] > 0 else 0

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
            df_profit_cols.to_csv(os.path.join(os.getenv("OUTPUT_DIR"), "test.csv"))

        return strategy_stat, curr_strategy_state['trade_history']

    except Exception as fault:
        print(f"Error occured while getting best strategy stats. error={fault}")
        traceback.print_exc()

def is_favourite_stock(strategy_stat: dict, ticker_name: str, \
                       manual_favourite_stocks: set) -> bool:
    
    # Find all the values in CheckpointProfit* keys that are greater than 30
    pattern = r'CheckpointProfit\d+'
    keys_to_check = [key for key in strategy_stat.keys() if re.match(pattern, key)]
    is_favourite = all(strategy_stat[key] > 30 for key in keys_to_check)
    
    return (ticker_name in manual_favourite_stocks) \
        or (
            is_favourite \
            and (strategy_stat['Profit'] > 100) \
            and (strategy_stat['Winrate'] >= 60)
        )
