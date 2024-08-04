import math
import pandas as pd
import ta
import traceback
import builtins
import concurrent.futures
import numpy as np
from lib.plots import plot_skewness

from lib.indicators import calculate_atr_trailing_stop
from lib.buy_sell import calculate_atr_buy_sell_signal
from lib.models import Transaction
from evaluate import service
import traceback


def calculate_max_drawdown(transactions):
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
        growth = ((end_price - start_price) / start_price) * 100
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
    sharpe_ratio = calculate_sharpe_ratio([t.abs_profit for t in transactions])
    skewness = calculate_skewness([t.abs_profit for t in transactions])
    return {
        'Wins': wins,
        'Losses': losses,
        'Entries': entries,
        'Exits': exits,
        'Winrate': round(winrate, 2),
        'Sharpe Ratio': sharpe_ratio,
        'Skewness': skewness
    }

def do_transactions(ticker_name, ticker_data, buy_columns, sell_column, transaction_stat, stock_growth):
    try:
        # Remove .NS from the ticker name
        if ticker_name.endswith('.NS'):
            ticker_name = ticker_name[:-3]

        # stock_growth, total_profit & winrate is in percentage
        transaction_stat = {
            'open_position': False,
            'Date': ticker_data.index[-1],
            'BuyColumns': None,
            'SellColumn': 'atrSellSignal',
            'Stock': ticker_name,
            'Profit': 0,
            'Stock Growth': stock_growth,
            'Wins': 0,
            'Losses': 0,
            'Entries': 0,
            'Exits': 0,
            'Winrate': 0,
            'Profit/StockGrowth': 0,
        }

        transactions = start_transactions(ticker_data, ticker_name, buy_columns, sell_column)
        # transactions_stat = summarise_transactions(transactions)
        
         

        builtins.logging.info(f"Transactions stat={transaction_stat}, Transactions={[str(t) for t in transactions]}")
        return transaction_stat, transactions

    except Exception as e:
        print(f"Error occured in while getting transaction stats. ticker={ticker_name}, error={e}")        
        builtins.logging.exception(f"Error occured in while getting transaction stats. ticker={ticker_name}, error={e}")        
        
def get_profit_column_name(buy_columns):
    return "profit_"+"_".join(buy_columns)

def start_transactions(df_ticker, symbol, buy_columns_combinations, sell_column, initial_captital=1000):
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
    try:
        df_with_profit_cols = pd.DataFrame(df_ticker)

        buy_price = None
        balance = initial_captital
        transaction = None
        open_positions = {
            # profit_col: Transaction
        }

        profit_till_date = {
            # profit_col: float
        }

        for buy_cols_combination in buy_columns_combinations:
            profit_column = get_profit_column_name(buy_cols_combination)
            df_with_profit_cols[profit_column] = None
        
        profit_till_date = 0
        
        # service.calculate_summarised_profit(transaction_stat, row)

        for i, row in df_with_profit_cols.iterrows():
            for buy_cols_combination in buy_columns_combinations:
                # Check if all the columns in buy_cols_combination is true
                # And there is no open position for the buy_cols_combination
                # Only then open a position against the buy_cols_combination
                open_transaction = open_positions.get(get_profit_column_name(buy_cols_combination))

                if all(df_with_profit_cols[col][i] for col in buy_cols_combination) \
                    and (open_transaction is None or not open_transaction.is_active()):

                    buy_price = df_with_profit_cols['Close'][i]
                    buy_quantity = balance / buy_price

                    # Open a position against the buy_cols_combination
                    open_positions[get_profit_column_name(buy_cols_combination)] = Transaction(symbol, buy_quantity, buy_price, df_with_profit_cols.index[i])

            # Check for a sell signal, calculate profit if a buy price is set, and reset transaction against the buy_cols_combination
            if df_with_profit_cols[sell_column][i]:
                for profit_column, transaction in open_positions.items():
                    sell_price = df_with_profit_cols['Close'][i]
                    transaction.end(sell_price, df_with_profit_cols.index[i])

                    profit_till_date += transaction.profit
                    df_with_profit_cols.iloc[i, df_with_profit_cols.columns.get_loc(profit_column)] = profit_till_date

        
        return df_with_profit_cols

    except Exception as fault:
        print(f"Error occured while starting transactions. error={fault}")
        traceback.print_exc()

def get_best_strategy_stats(ticker_name, stock_growth, ticker_data, sell_column, buy_columns_combinations):
    # stock_growth, total_profit & winrate is in percentage    
    transaction_stat = {
        'open_position': False,
        'Date': ticker_data.index[-1],
        'BuyColumns': None,
        'SellColumn': 'atrSellSignal',
        'Stock': ticker_name,
        'Profit': 0,
        'Stock Growth': stock_growth,
        'Wins': 0,
        'Losses': 0,
        'Entries': 0,
        'Exits': 0,
        'Winrate': 0,
        'Profit/StockGrowth': 0,
    }

    futures = []

    # with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
    #     futures.extend(
    #         executor.submit(
    #             get_transactions_summary,
    #             ticker_name,
    #             ticker_data,
    #             buy_cols_combination,
    #             sell_column,
    #         )
    #         for buy_cols_combination in buy_columns_combinations
    #     )
    
    do_transactions(ticker_name, ticker_data, buy_columns_combinations, sell_column, transaction_stat, stock_growth)
                
    
    # for future in concurrent.futures.as_completed(futures):
    #     df_with_profit_cols = future.result()

    # for buy_cols_combination in buy_columns_combinations:
    #     # It will populate ticke_data with profit_indicator columns
    #     _, transactions = get_transactions_summary(
    #         ticker_name,
    #         ticker_data,
    #         buy_cols_combination,
    #         sell_column,
    #     )

    # ticker_data.to_csv(r"C:\Users\mrina\OneDrive\Documents\projects\UTBotStochasticRsi\python\output\dummy.csv")
    
    # Populate transaction_stat
    # for index, row in df_with_profit_cols.iterrows():
    #     service.calculate_summarised_profit(transaction_stat, row)

    builtins.logging.info(f"Ticker Name: {ticker_name}, Best transactions_stat: {transaction_stat}")

    print(f"Calculated most profitable buy combination. ticker name={ticker_name}")
    return transaction_stat

def calculate_sharpe_ratio(returns, risk_free_rate=0.05):
    """
    Calculate the Sharpe Ratio for the given returns.

    Parameters
    ----------
    returns : array-like
        The returns for which the Sharpe Ratio is to be calculated.
    risk_free_rate : float, optional
        The risk-free rate of return, by default 0.0

    Returns
    -------
    float
        The Sharpe Ratio.
    """
    if not returns:
        return np.nan
    # Convert returns to a numpy array if it's not already
    returns = np.array(returns)

    # Calculate the excess returns by subtracting the risk-free rate
    excess_returns = returns - risk_free_rate

    # Calculate the mean of excess returns
    mean_excess_returns = np.mean(excess_returns)

    # Calculate the standard deviation of returns
    std_dev_returns = np.std(returns)

    # Calculate the Sharpe Ratio
    if std_dev_returns == 0:
        return np.nan  # Return NaN if standard deviation is zero to avoid division by zero

    return round(mean_excess_returns / std_dev_returns, 2)

def calculate_skewness(data):
    """
    Calculate the skewness of the given data and plot its distribution.

    Parameters
    ----------
    data : array-like
        The data for which the skewness is to be calculated.

    Returns
    -------
    float
        The skewness of the data.
    """
    if not data:
        return np.nan
    # Convert data to a numpy array if it's not already
    data = np.array(data)

    # Calculate the mean of the data
    mean_data = np.mean(data)

    # Calculate the standard deviation of the data
    std_dev_data = np.std(data)
    if std_dev_data == 0:
        return np.nan

    # Calculate the skewness using the formula for skewness
    skewness = np.sum((data - mean_data) ** 3) / (len(data) * (std_dev_data ** 3))
    skewness = round(skewness, 2)

    return skewness