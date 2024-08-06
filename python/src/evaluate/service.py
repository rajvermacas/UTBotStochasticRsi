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

def find_best_strategy_stat(args, row):
    transactions_summary, buy_cols_combinations, ticker_name = args
    sell_column = 'atrSellSignal'

    max_profit = 0
    best_signal_column_combination = None

    # Only take trade when not in trade already
    if not transactions_summary['open_position']:
        for signal_cols in buy_cols_combinations:
            profit_col = get_profit_column_name(signal_cols)

            if row[profit_col] and row[profit_col] > max_profit:
                max_profit = row[profit_col]
                best_signal_column_combination = signal_cols
                transactions_summary['BuyColumns'] = signal_cols

        # Check if the most profitable strategy is giving a buy signal
        if best_signal_column_combination and all(
            row[signal_col] for signal_col in best_signal_column_combination
        ):
            # Open position
            transactions_summary['open_position'] = True
            transactions_summary['profit_column'] = get_profit_column_name(best_signal_column_combination)
            transactions_summary['Entries'] = transactions_summary.get('Entries', 0) + 1
            transactions_summary['BuyDate'] = row.name

            buy_quantity = params.CAPITAL/row['Close']
            transactions_summary['TradeHistory'].append(
                Transaction(ticker_name, buy_quantity, row['Close'], row.name, transactions_summary['BuyColumns'])
            )

            # print(f"Opening position. strategy={transactions_summary['profit_column']} date of purchase={row['Date']}")

    # If there is a sell siganl, book profit
    if transactions_summary['open_position'] and row[sell_column]:
        _populate_transactions_summary(transactions_summary, row)
    
def _populate_transactions_summary(transactions_summary, row):
    transaction = transactions_summary['TradeHistory'][-1]
    transaction.end(row['Close'], row.name)

    # profit = row[transactions_summary['profit_column']]
    profit_perc = transaction.profit_perc

    transactions_summary['open_position'] = False
    transactions_summary['Exits'] = transactions_summary.get('Exits', 0) + 1
    transactions_summary['Wins'] = transactions_summary.get('Wins', 0) + (profit_perc > transactions_summary['Profit'])
    transactions_summary['Losses'] = transactions_summary.get('Losses', 0) + (profit_perc < transactions_summary['Profit'])
    transactions_summary['Profit'] = transactions_summary.get('Profit', 0) + round(profit_perc, 2)
    transactions_summary['Winrate'] = round((transactions_summary['Wins'] / transactions_summary['Exits']) * 100, 2)

    if transactions_summary['Stock Growth'] < 0 and transactions_summary['Profit'] < 0:
        transactions_summary['Profit/StockGrowth'] = -round(transactions_summary['Profit'] / transactions_summary['Stock Growth'], 2)
    else:
        transactions_summary['Profit/StockGrowth'] = round(transactions_summary['Profit'] / transactions_summary['Stock Growth'], 2)
    
    # transactions_summary['TradeHistory'].append({
    #     'Stock': transactions_summary['Stock'],
    #     'BuyDate': transactions_summary['BuyDate'].strftime('%Y-%m-%d'),
    #     'SellDate': row.name.strftime('%Y-%m-%d'),
    #     'ProfitPerc': round(transactions_summary['Profit'], 2),
    #     'BuyColumns': transactions_summary['BuyColumns'],
    # })