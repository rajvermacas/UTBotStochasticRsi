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
import os
import params as app_params


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
    """
    Summarise a list of transactions into key statistics.

    Parameters:
    transactions (list): A list of transaction objects.

    Returns:
    dict: A dictionary containing the number of wins, losses, entries, exits, winrate, Sharpe ratio, and skewness.
    """
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
        df_profit_cols = populate_profit_cols(df_ticker, ticker_name, buy_columns_combinations, sell_column)

        # Prepare temporary strategy state for function find_best_strategy_stat
        curr_strategy_state = {
            'open_position': False,
            'buy_columns': None,
            'trade_history': [],
        }
        
        args = (curr_strategy_state, buy_columns_combinations, ticker_name)
        df_profit_cols.apply(partial(service.find_best_transactions, args), axis=1)

        # Profit, stock growth, winrate is in percentage
        transactions_summary = {
            'Stock': ticker_name,
            'Date': df_ticker.index[-1],
            'Stock Growth': stock_growth,
            'Wins': 0,
            'Losses': 0,
            'Entries': 0,
            'Exits': 0,
            'Winrate': 0,
            'Profit': 0,
            'Profit/StockGrowth': 0,
        }

        best_strategy_stat = service.summarise_transactions(curr_strategy_state['trade_history'])
        transactions_summary.update(best_strategy_stat)

        if transactions_summary['Stock Growth'] < 0 and transactions_summary['Profit'] < 0:
            transactions_summary['Profit/StockGrowth'] = -round(transactions_summary['Profit'] / transactions_summary['Stock Growth'], 2)

        else:
            transactions_summary['Profit/StockGrowth'] = round(transactions_summary['Profit'] / transactions_summary['Stock Growth'], 2)
        
        # print(f"Stock={ticker_name} Trade history={[str(transaction) for transaction in transactions_summary['TradeHistory']]}")
        builtins.logging.info(f"Stock={ticker_name} Trade history={[str(transaction) for transaction in curr_strategy_state['trade_history']]}")

        if os.environ.get('EXECUTION_MODE') == app_params.EXECUTION_MODE_TEST:
            df_profit_cols.to_csv(os.path.join(os.getenv("ROOT_DIR"), "test.csv"))

        return transactions_summary

    except Exception as fault:
        print(f"Error occured while getting best strategy stats. error={fault}")
        traceback.print_exc()

def populate_profit_cols(df_ticker, ticker_name, buy_columns_combinations, sell_column):
    """
    This function calculates and populates the profit columns for a given ticker.

    It takes in the following parameters:
    - df_ticker: A pandas DataFrame containing the ticker data.
    - ticker_name: The name of the ticker.
    - buy_columns_combinations: A list of combinations of columns to use for buying signals.
    - sell_column: The column to use for selling signals.

    It returns a pandas DataFrame with the profit columns populated.
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
        
    def process_row(row):
        """
        Process a single row of data.

        Args:
            row (pandas.Series): The row of data to process.

        Returns:
            pandas.Series: The processed row of data.

        This function takes a row of data and performs the following operations:
        1. It calls the `open_long_position` function with the ticker name, buy columns combinations, the row, the capital, the open positions, and the index.
        2. It checks if the row contains a sell signal. If it does, it calls the `close_long_position` function with the ticker name, the row, the open positions, the profit percentage till date, and the index.
        3. It iterates over the buy columns combinations and calculates the profit column name.
        4. It retrieves the profit percentage for the current row from the `profit_perc_till_date` dictionary.
        5. It assigns the profit percentage to the corresponding profit column in the row.
        6. It returns the processed row.
        """
        index = row.name
        open_long_position(ticker_name, buy_columns_combinations, row, params.CAPITAL, open_positions, index)

        if row[sell_column]:
            close_long_position(ticker_name, row, open_positions, profit_perc_till_date, index)
        
        for buy_cols_combination in buy_columns_combinations:
            profit_column = get_profit_column_name(buy_cols_combination)
            row[profit_column] = profit_perc_till_date.get(profit_column, 0)
        
        return row

    df_with_profit_cols = df_with_profit_cols.apply(process_row, axis=1)

    return df_with_profit_cols

def close_long_position(ticker_name, row, open_positions, profit_perc_till_date, index):
    """
    Closes a long position for the given ticker.

    Args:
        ticker_name (str): The name of the ticker.
        row (pandas.Series): The row of data containing the close price.
        open_positions (dict): A dictionary of open positions.
        profit_perc_till_date (dict): A dictionary of profit percentages till date.
        index (Timestamp): The index of the current row i.e the date.

    Returns:
        None
    """
    for profit_column, transaction in open_positions.items():
        # If no transaction is active then no need to close position
        if transaction.is_active():
            sell_price = row['Close']
            transaction.end(sell_price, index)

            profit_perc_till_date[profit_column] = profit_perc_till_date.get(profit_column, 0) + transaction.profit_perc
            # print(f"Closing position. stock={ticker_name} profit={transaction.profit_perc} strategy={profit_column} date of purchase={index}")

def open_long_position(ticker_name, buy_columns_combinations, row, balance, open_positions, index):
    """
    Opens a long position for the given ticker.

    Args:
        ticker_name (str): The name of the ticker.
        buy_columns_combinations (list): A list of combinations of buy columns.
        row (pandas.Series): The row of data containing the necessary information.
        balance (float): The available balance for trading.
        open_positions (dict): A dictionary of open positions.
        index (int): The index of the current row.

    Returns:
        None

    This function iterates over the buy columns combinations and checks if all the columns in the combination are true.
    If a combination satisfies this condition and there is no open position for the combination, it opens a position against the combination.
    The position is opened by creating a Transaction object with the ticker name, buy quantity, buy price, index, and buy columns combination.
    The Transaction object is then added to the open_positions dictionary using the profit column name as the key.
    """
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