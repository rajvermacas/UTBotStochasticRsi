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

from lib.models import Transaction
from lib import params

def get_profit_column_name(signal_columns):
    return "profit_"+"_".join(signal_columns)

def find_best_transactions(args, row):
    curr_strategy_state, buy_cols_combinations, ticker_name = args
    sell_column = 'atrSellSignal'

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

            buy_quantity = params.CAPITAL/row['Close']
            curr_strategy_state['trade_history'].append(
                Transaction(ticker_name, buy_quantity, row['Close'], row.name, curr_strategy_state['buy_columns'])
            )

    # If there is a sell siganl, book profit
    if curr_strategy_state['open_position'] and row[sell_column]:
        transaction = curr_strategy_state['trade_history'][-1]
        transaction.end(row['Close'], row.name)
        curr_strategy_state['open_position'] = False

    
def summarise_transactions(transactions):
    wins = 0
    losses = 0
    entries = 0
    exits = 0
    profit_and_loss = 0
    profit_perc = 0

    for transaction in transactions:
        if transaction.sell_price > transaction.buy_price:
            wins += 1
        else:
            losses += 1

        entries += 1
        exits += 1
        profit_perc += transaction.profit_perc

    winrate = 0
    if entries > 0:
        winrate = round((wins / entries) * 100, 2)

    profit_and_loss = 0
    if exits > 0:
        profit_and_loss = round((wins - losses) / exits, 2)

    return {
        'Wins': wins,
        'Losses': losses,
        'Entries': entries,
        'Exits': exits,
        'Winrate': winrate,
        'Profit/StockGrowth': profit_and_loss,
        'Profit': round(profit_perc, 2),
    }
    