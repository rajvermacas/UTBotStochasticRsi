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
from lib import params
from evaluate import service
import traceback
from functools import partial


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

def get_profit_column_name(buy_columns):
    """
    Input sample: ['atrBuySignal', 'rsiBuySignal', 'stochasticBuySignal']
    Output sample: 'profit_atrBuySignal_rsiBuySignal_stochasticBuySignal'
    """
    return "profit_"+"_".join(buy_columns)

def get_best_strategy_stats(ticker_name, stock_growth, df_ticker, sell_column, buy_columns_combinations):
    try:
        df_profit_cols = populate_profit_cols(df_ticker, ticker_name, buy_columns_combinations, sell_column)
            
        # todo: Take it out of the iterrows loop and use df.apply and restore original evaluate service and check time taken
        # Profit, stock growth, winrate is in percentage
        # BuyColumns is a list of signal columns (string)
        transactions_summary = {
            'open_position': False,
            'Date': df_ticker.index[-1],
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
            'BuyDate': None,
            'TradeHistory': [],
        }
        
        args = (transactions_summary, buy_columns_combinations, ticker_name)
        df_profit_cols.apply(partial(service.find_best_strategy_stat, args), axis=1)
        
        # print(f"Stock={ticker_name} Trade history={[str(transaction) for transaction in transactions_summary['TradeHistory']]}")
        builtins.logging.info(f"Stock={ticker_name} Trade history={[str(transaction) for transaction in transactions_summary['TradeHistory']]}")
        df_profit_cols.to_csv(r"C:\Users\mrina\OneDrive\Documents\projects\UTBotStochasticRsi\python\output\test.csv")
        
        return transactions_summary

    except Exception as fault:
        print(f"Error occured while getting best strategy stats. error={fault}")
        traceback.print_exc()

def populate_profit_cols(df_ticker, ticker_name, buy_columns_combinations, sell_column):
    """
    It will add profit_cols i.e. 
    'profit_atrBuySignal',
    'profit_rsiBuySignal',
    'profit_stochasticBuySignal',
    'profit_atrBuySignal_rsiBuySignal',
    'profit_atrBuySignal_stochasticBuySignal',
    'profit_rsiBuySignal_stochasticBuySignal',
    'profit_atrBuySignal_rsiBuySignal_stochasticBuySignal'

    These columns will contain profit percentage till date
    """
    open_positions = {
        # profit_col: Transaction
    }

    profit_perc_till_date = {
        # profit_col: float
    }

    df_with_profit_cols = pd.DataFrame(df_ticker)

    for buy_cols_combination in buy_columns_combinations:
        profit_column = get_profit_column_name(buy_cols_combination)
        df_with_profit_cols[profit_column] = None
        
    for index, row in df_with_profit_cols.iterrows():
        open_long_position(ticker_name, buy_columns_combinations, row, params.CAPITAL, open_positions, index)

            # Check for a sell signal, calculate profit if a buy price is set, and reset transaction against the buy_cols_combination
        if row[sell_column]:
            close_long_position(ticker_name, row, open_positions, profit_perc_till_date, index)
            
        for buy_cols_combination in buy_columns_combinations:
            profit_column = get_profit_column_name(buy_cols_combination)
            df_with_profit_cols.loc[index, profit_column] = profit_perc_till_date.get(profit_column, 0)

    return df_with_profit_cols

def close_long_position(ticker_name, row, open_positions, profit_perc_till_date, index):
    for profit_column, transaction in open_positions.items():
        # If no transaction is active then no need to close position
        if transaction.is_active():
            sell_price = row['Close']
            transaction.end(sell_price, index)

            profit_perc_till_date[profit_column] = profit_perc_till_date.get(profit_column, 0) + transaction.profit_perc
            # print(f"Closing position. stock={ticker_name} profit={transaction.profit_perc} strategy={profit_column} date of purchase={index}")

def open_long_position(ticker_name, buy_columns_combinations, row, balance, open_positions, index):
    for buy_cols_combination in buy_columns_combinations:
        # Check if all the columns in buy_cols_combination are true
        # And there is no open position for the buy_cols_combination
        # Only then open a position against the buy_cols_combination
        open_transaction = open_positions.get(get_profit_column_name(buy_cols_combination))

        if all(row[col] for col in buy_cols_combination) \
                    and (open_transaction is None or not open_transaction.is_active()):
            buy_price = row['Close']
            buy_quantity = balance / buy_price

            # Open a position against the buy_cols_combination
            open_positions[get_profit_column_name(buy_cols_combination)] = Transaction(ticker_name, buy_quantity, buy_price, index, buy_cols_combination)

            # print(f"Opening position. stock={ticker_name} strategy={get_profit_column_name(buy_cols_combination)} date of purchase={index}")

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