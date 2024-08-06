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

def find_best_strategy_stat(transaction, index, df):
    sell_column = 'atrSellSignal'

    max_profit = 0
    best_signal_column_combination = None

    # Only take trade when not in trade already
    if not transaction['open_position']:
        for signal_cols, profit_col in zip(signal_columns, profit_columns):
            if df.loc[index, profit_col] and df.loc[index, profit_col] > max_profit:
                max_profit = df.loc[index, profit_col]
                best_signal_column_combination = signal_cols
                transaction['BuyColumns'] = signal_cols

        # Check if the most profitable strategy is giving a buy signal
        if best_signal_column_combination and all(
            df.loc[index, signal_col] for signal_col in best_signal_column_combination
        ):
            transaction['open_position'] = True
            transaction['profit_column'] = get_profit_column_name(best_signal_column_combination)
            transaction['Entries'] = transaction.get('Entries', 0) + 1
            transaction['BuyDate'] = index

            # print(f"Opening position. strategy={transaction['profit_column']} date of purchase={row['Date']}")

    # If there is a sell siganl, book profit
    if transaction['open_position'] and df.loc[index, sell_column]:
        profit = df.loc[index, transaction['profit_column']]
        _populate_transaction(transaction, profit)

        return {
            'Stock': transaction['Stock'],
            'BuyDate': transaction['BuyDate'].strftime('%Y-%m-%d'),
            'SellDate': index.strftime('%Y-%m-%d'),
            'ProfitPerc': round(transaction['Profit'], 2),
            'BuyColumns': transaction['BuyColumns'],
        }
    
    # If profit is not booked then return None
    return None


def _populate_transaction(transaction, profit):
    transaction['open_position'] = False

    transaction['Exits'] = transaction.get('Exits', 0) + 1
    transaction['Wins'] = transaction.get('Wins', 0) + (profit > transaction['Profit'])
    transaction['Losses'] = transaction.get('Losses', 0) + (profit < transaction['Profit'])

    transaction['Profit'] = round(profit, 2)
    transaction['Winrate'] = round((transaction['Wins'] / transaction['Exits']) * 100, 2)

    if transaction['Stock Growth'] < 0 and transaction['Profit'] < 0:
        transaction['Profit/StockGrowth'] = -round(transaction['Profit'] / transaction['Stock Growth'], 2)
    else:
        transaction['Profit/StockGrowth'] = round(transaction['Profit'] / transaction['Stock Growth'], 2)

    return profit