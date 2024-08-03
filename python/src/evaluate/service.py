# List of profit indicator columns
# Profit columns by default are cumulated till date
profit_columns = [
    'profit_atrBuySignal',
    'profit_rsiBuySignal',
    'profit_stochasticBuySignal',
    'profit_atrBuySignal_rsiBuySignal',
    'profit_atrBuySignal_stochasticBuySignal',
    'profit_rsiBuySignal_stochasticBuySignal',
    'profit_atrBuySignal_rsiBuySignal_stochasticBuySignal'
]

# Corresponding signal columns
signal_columns = [
    ['atrBuySignal'],
    ['rsiBuySignal'],
    ['stochasticBuySignal'],
    ['atrBuySignal', 'rsiBuySignal'],
    ['atrBuySignal', 'stochasticBuySignal'],
    ['rsiBuySignal', 'stochasticBuySignal'],
    ['atrBuySignal', 'rsiBuySignal', 'stochasticBuySignal']
]


def get_profit_column_name(signal_columns):
    return "profit_"+"_".join(signal_columns)

def calculate_summarised_profit(transaction, row):
    sell_column = 'atrSellSignal'

    max_profit = 0
    best_signal_column_combination = None

    # Only take trade when not in trade already
    if not transaction['open_position']:
        for signal_col, profit_col in zip(signal_columns, profit_columns):
            if row[profit_col] > max_profit:
                max_profit = row[profit_col]
                best_signal_column_combination = signal_col

        # Check if the most profitable strategy is giving a buy signal
        if best_signal_column_combination and all(
            row[signal_col] for signal_col in best_signal_column_combination
        ):
            transaction['open_position'] = True
            transaction['profit_column'] = get_profit_column_name(best_signal_column_combination)
            transaction['Entries'] = transaction.get('Entries', 0) + 1
            # print(f"Opening position. strategy={transaction['profit_column']} date of purchase={row['Date']}")

    # If there is a sell siganl, book profit
    if transaction['open_position'] and row[sell_column]:
        return _populate_transaction(transaction, row)
    
    # If profit is not booked then return None
    return None


def _populate_transaction(transaction, row):
    transaction['open_position'] = False

    result = row[transaction['profit_column']]
    transaction['buy_columns_combinations'] = None

    transaction['Exits'] = transaction.get('Exits', 0) + 1
    transaction['Wins'] = transaction.get('Wins', 0) + (result > transaction['Profit'])
    transaction['Losses'] = transaction.get('Losses', 0) + (result < transaction['Profit'])

    transaction['Profit'] = round(result, 2)
    transaction['Winrate'] = round((transaction['Wins'] / transaction['Exits']) * 100, 2)

    if transaction['Stock Growth'] < 0 and transaction['Profit'] < 0:
        transaction['Profit/StockGrowth'] = -round(transaction['Profit'] / transaction['Stock Growth'], 2)
    else:
        transaction['Profit/StockGrowth'] = round(transaction['Profit'] / transaction['Stock Growth'], 2)

    return result