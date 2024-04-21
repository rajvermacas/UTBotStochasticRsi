import math
import pandas as pd
import ta
import traceback
import builtins
import concurrent.futures

from lib.indicators import calculate_atr_trailing_stop
from lib.buy_sell import calculate_atr_buy_sell_signal
from lib.models import Transaction


def calculate_max_drawdown(transactions):
    # Todo
    """
    Calculate the maximum drawdown from a list of transactions.
    
    Parameters:
    transactions (list): A list of Transaction objects.
    
    Returns:
    float: The maximum drawdown as a percentage.
    """
    peak = -float('inf')
    max_drawdown = 0
    
    for transaction in transactions:
        peak = max(peak, transaction.sell_price)
        drawdown = (peak - transaction.sell_price) / peak * 100
        max_drawdown = max(max_drawdown, drawdown)
    
    return max_drawdown

def calculate_stock_growth(data, start_date, end_date):
    # sourcery skip: inline-immediately-returned-variable, inline-variable, remove-unnecessary-else, swap-if-else-branches
    """
    Calculate the growth of a stock between two dates.

    Parameters:
    data (DataFrame): The stock data.
    start_date (str): The start date in 'YYYY-MM-DD' format.
    end_date (str): The end date in 'YYYY-MM-DD' format.

    Returns:
    float: The growth of the stock as a percentage.
    """
    # Filter the data for the given date range
    filtered_data = data.loc[start_date:end_date]
    
    # Ensure there is data for both start and end dates
    if not filtered_data.empty:
        start_price = filtered_data.iloc[0]['Close']
        end_price = filtered_data.iloc[-1]['Close']
        
        # Calculate growth
        growth = (end_price - start_price) / start_price * 100
        growth = round(growth, 2)
        return growth or 0.01
    else:
        return None

def summarise_transactions(transactions):
    wins = sum(t.profit and t.profit > 0 for t in transactions)
    losses = sum(t.profit and t.profit < 0 for t in transactions)
    entries = len(transactions)
    exits = len([t for t in transactions if t.sell_price is not None])
    winrate = wins / exits * 100 if exits > 0 else 0
    return {
        'Wins': wins,
        'Losses': losses,
        'Entries': entries,
        'Exits': exits,
        'Winrate': round(winrate, 2),
    }

def get_transactions_summary(ticker_name, ticker_data, buy_columns, sell_column):
    try:
        transactions, profit = start_transactions(ticker_data, ticker_name, buy_columns, sell_column)
        transactions_stats = summarise_transactions(transactions)

        result = {
            'Stock': ticker_name, 
            'Profit': round(profit, 2), 
            'BuyColumns': ",".join(buy_columns), 
            'SellColumn': sell_column,
        }
        result |= transactions_stats

        builtins.logging.info(f"result={result}, Transactions={[str(t) for t in transactions]}")
        return result

    except Exception as e:
        print(f"Error occured in while getting transaction stats. ticker={ticker_name}, error={e}")        
        builtins.logging.exception(f"Error occured in while getting transaction stats. ticker={ticker_name}, error={e}")        
        
def find_best_atr_combination(data, ticker, atr_sensitivity_range, atr_period_range):
    max_profit = -float('inf')
    best_combination = (0, 0)

    for sensitivity in range(atr_sensitivity_range[0], atr_sensitivity_range[1]):
        for period in range(atr_period_range[0], atr_period_range[1]):
            atr_column = calculate_atr_trailing_stop(data, sensitivity, period)
            atr_buy_column, atr_sell_column = calculate_atr_buy_sell_signal(data)

            _, profit = start_transactions(data, ticker, atr_buy_column, atr_sell_column)
            if profit > max_profit:
                max_profit = profit
                best_combination = (sensitivity, period)
                print(
                    f"Intermediate: best_combination={best_combination}, best profit={max_profit}"
                )

    return best_combination, max_profit

def start_transactions(data, symbol, buy_columns, sell_column, initial_captital=1000):
    """
    Calculate profit based on buy and sell signals.
    
    Parameters
    ----------
    data : pandas.DataFrame
        The DataFrame containing the stock data along with buy and sell signals.
    
    Returns
    -------
    total_profit : float
        The total profit calculated from the buy and sell signals.
    """
    buy_price = None
    balance = initial_captital
    transaction = None
    transactions = []

    for i in range(len(data)):
        # Check for a buy signal and remember the transaction
        if all(data[col][i] for col in buy_columns) and transaction is None:
            buy_price = data['Close'][i]
            buy_quantity = balance / buy_price
            transaction = Transaction(symbol, buy_quantity, buy_price, data.index[i])

        # Check for a sell signal, calculate profit if a buy price is set, and reset transaction
        if data[sell_column][i] and transaction is not None:
            sell_price = data['Close'][i]
            profit = transaction.end(sell_price, data.index[i])
            balance += profit
            
            transactions.append(transaction)
            transaction = None
    
    return transactions, (balance-initial_captital)/initial_captital * 100

def calculate_most_profitable_buy_combination(ticker_name, stock_growth, futures):
    best_transactions_stat = None

    for future in concurrent.futures.as_completed(futures):
        transactions_stat = future.result()
        if best_transactions_stat is None or transactions_stat['Profit'] > best_transactions_stat['Profit']:
            best_transactions_stat = transactions_stat
                
    builtins.logging.info(f"Ticker Name: {ticker_name}, Best transactions_stat: {best_transactions_stat}")

    best_transactions_stat['Stock Growth'] = stock_growth
                
    if stock_growth < 0 and best_transactions_stat['Profit'] < 0:
        best_transactions_stat['Profit/StockGrowth'] = -round(best_transactions_stat['Profit']/stock_growth, 2)
    else:
        best_transactions_stat['Profit/StockGrowth'] = round(best_transactions_stat['Profit']/stock_growth, 2)

    return best_transactions_stat