import ta
import pandas as pd
from itertools import combinations
import builtins

from indicator import service as indicator_service
from lib import params as app_params
import pandas as pd
import ta
from lib.models import Transaction
from lib import params
import lib.params as app_params


def get_profit_column_name(signal_columns):
    """
    Input sample: ['atrBuySignal', 'rsiBuySignal', 'stochasticBuySignal']
    Output sample: 'profit_atrBuySignal_rsiBuySignal_stochasticBuySignal'
    """
    return "profit_"+"_".join(signal_columns)

def calculate_atr_trailing_stop(data: pd.DataFrame, atr_sensitivity=2, atr_period=3):
    """
    Calculate ATR Trailing Stop
    ------------------------------------
    This function calculates the ATR Trailing Stop using the given data,
    atr_sensitivity and atr_period.
    The ATR Trailing Stop is a trading stop loss strategy that is based on the Average True Range (ATR).
    
    The ATR Trailing Stop is calculated using the following formula:
        ATR Trailing Stop = Price - (ATR Sensitivity * ATR)
        
    The ATR Sensitivity is a user-defined parameter that adjusts the stop loss based on the desired risk level.
    
    The ATR is calculated using the Wilder's method, which is a simple moving average of the True Range values.
    The True Range is calculated as the maximum of the following:
        High - Low
        Abs(High - Previous Close)
        Abs(Low - Previous Close)
    
    The ATR is then calculated as the Exponential Moving Average (EMA) of the True Range using the ATR period.
    
    The ATR Trailing Stop is calculated for each bar, and it is an updated version of the previous ATR Trailing Stop.
    If the current price is above the previous ATR Trailing Stop, then the ATR Trailing Stop is updated to:
        ATR Trailing Stop = Current Price - (ATR Sensitivity * ATR)
    If the current price is below the previous ATR Trailing Stop, then the ATR Trailing Stop is updated to:
        ATR Trailing Stop = Current Price + (ATR Sensitivity * ATR)
    
    The ATR Trailing Stop is an updated version of the previous ATR Trailing Stop, and it is only updated when the current
    price is above or below the previous ATR Trailing Stop. When the price crosses the ATR Trailing Stop, the ATR Trailing
    Stop is recalculated using the current price and the ATR Sensitivity and ATR.
    
    Parameters
    ----------
    data : pandas.DataFrame
        A DataFrame containing the historical price data.
        The index is the date of the data, the columns are the symbol(s) and the values are the respective prices.
    atr_sensitivity : int
        ATR sensitivity, adjust based on your strategy
    atr_period : int
        Commonly used period for ATR
    
    Returns
    -------
    x_atr_trailing_stop : pandas.Series
        A Series containing the calculated ATR Trailing Stop values
        The index is the same as the data and the name is 'ATR_TS'
    """
    try:
        # Calculate ATR
        atr = ta.volatility.AverageTrueRange(data['High'], data['Low'], data['Close'], window=atr_period).average_true_range()
        
        # Calculate N loss based on ATR sensitivity
        n_loss = atr_sensitivity * atr
        
        # Initialize the ATR Trailing Stop Series with zeros
        x_atr_trailing_stop = pd.Series([0.0] * len(data), index=data.index, name='ATR_TS')
        
        for i in range(1, len(data)):
            src = data['Close'][i]
            
            # Calculate ATR Trailing Stop
            if src > x_atr_trailing_stop[i-1]:
                x_atr_trailing_stop[i] = src - n_loss[i]
            else:
                x_atr_trailing_stop[i] = src + n_loss[i]
            
            # Handle case when the price falls below previous ATR Trailing Stop
            if src < x_atr_trailing_stop[i-1] and data['Close'][i-1] < x_atr_trailing_stop[i-1]:
                x_atr_trailing_stop[i] = min(x_atr_trailing_stop[i-1], src + n_loss[i])
            # Handle case when the price rises above previous ATR Trailing Stop
            else:
                x_atr_trailing_stop[i] = max(x_atr_trailing_stop[i-1], src - n_loss[i]) if src > x_atr_trailing_stop[i-1] and data['Close'][i-1] > x_atr_trailing_stop[i-1] else x_atr_trailing_stop[i]
        
        column_name = 'ATR_TS'
        data[column_name] = x_atr_trailing_stop
        return column_name
    
    except Exception as fault:
        builtins.logging.error("Error calculating ATR Trailing Stop: " + str(fault))
        raise Exception("Error calculating ATR Trailing Stop: " + str(fault))

def calculate_stochastic(data, k_length=14, k_smooth_period=3, d_smooth_period=3):
    """
    Calculate custom stochastic oscillator based on the formula:
    100 * (close - lowest(low, length)) / (highest(high, length) - lowest(low, length))
    
    Parameters:
    - data: DataFrame containing 'Close', 'High', and 'Low' columns
    - length: The period over which to calculate the lowest low and highest high
    
    Returns:
    - A pandas Series representing the custom stochastic values
    """
    try:
        lowest_low = data['Low'].rolling(window=k_length).min()
        highest_high = data['High'].rolling(window=k_length).max()
        close = data['Close']
        
        # for rescaling the values from (-100 to 100) to (0 to 100)
        fast_k = ( (100 * (close - lowest_low) / (highest_high - lowest_low) ) + 100) * 0.5
        smooth_fast_k = ta.trend.sma_indicator(fast_k, window=k_smooth_period)
        fast_d = ta.trend.sma_indicator(smooth_fast_k, window=d_smooth_period)

        return smooth_fast_k, fast_d
    except Exception as fault:
        raise Exception("Error calculating Stochastic: " + str(fault))

def calculate_rsi_buy_signal(data, rsi_period=14, ema_period=14):
    # sourcery skip: inline-immediately-returned-variable
    rsi_indicator = ta.momentum.RSIIndicator(data['Close'], window=rsi_period)
    rsi = rsi_indicator.rsi()
    ema_rsi = ta.trend.EMAIndicator(rsi, ema_period).ema_indicator()

    rsi_buy_column = 'rsiBuySignal'
    # rsi is above 50
    # and rsi is above ema_rsi 
    # and ema_rsi is above 40 
    # and close is above ATR
    data[rsi_buy_column] = (rsi >= 50) & (rsi > ema_rsi) & (ema_rsi > 40) & (data['Close'] >= data['ATR_TS'])

    # Generate buy Signal only at the first buy signal after a sell signal
    sell_column = app_params.ATR_SELL_COLUMN
    buy_signal_generated = False
    for i in range(len(data)):
        if data[sell_column][i] and buy_signal_generated:
            buy_signal_generated = False  # Reset buy signal flag after a sell signal
        if not buy_signal_generated and data[rsi_buy_column][i]:
            buy_signal_generated = True  # Set buy signal flag
        else:
            data.loc[data.index[i], rsi_buy_column] = False  # Do not generate buy signal if already generated
    
    return rsi_buy_column

def calculate_stochastic_buy_signal(data):
    # sourcery skip: inline-immediately-returned-variable
    # Calculate %K and %D
    k, d = indicator_service.calculate_stochastic(data)
    data['%K'] = k
    data['%D'] = d
    
    # stochasticBuySignal = %K > %D 
    # and %D < 60
    # and close is above ATR
    stochasticBuySignal = (data['%K'] > data['%D']) & (data['%D'] < 60) & (data['Close'] >= data['ATR_TS'])

    stochastic_buy_column = 'stochasticBuySignal'
    data[stochastic_buy_column] = stochasticBuySignal

    # Generate buy Signal only at the first buy signal after a sell signal
    sell_column = app_params.ATR_SELL_COLUMN
    buy_signal_generated = False
    for i in range(len(data)):
        if data[sell_column][i] and buy_signal_generated:
            buy_signal_generated = False  # Reset buy signal flag after a sell signal
        if not buy_signal_generated and data[stochastic_buy_column][i]:
            buy_signal_generated = True  # Set buy signal flag
        else:
            data.loc[data.index[i], stochastic_buy_column] = False  # Do not generate buy signal if already generated

    return stochastic_buy_column

def calculate_atr_buy_sell_signal(data):
    """
    Ensure this is called after ATR_TS is calculated
    """
    atr_buy_column = 'atrBuySignal'
    atr_sell_column = app_params.ATR_SELL_COLUMN
    # Assuming 'data' is your DataFrame and it has a 'Close' column
    data['EMA_1'] = ta.trend.ema_indicator(data['Close'], window=1)

    # To calculate the sell signal based on a crossover, we need to shift the EMA series to compare the current value with the previous one
    data['EMA_1_shifted'] = data['EMA_1'].shift(1)

    # Assuming ATR_TS is a pandas Series calculated previously
    data['ATR_TS_shifted'] = data['ATR_TS'].shift(1)

    # Detecting crossover: ATR_TS crosses over EMA
    data[atr_sell_column] = (data['ATR_TS'] > data['EMA_1']) & (data['ATR_TS_shifted'] <= data['EMA_1_shifted'])

    # Convert Pine Script code to Python
    # Calculate the buy signal based on a crossover of EMA and ATR_TS
    data[atr_buy_column] = (data['EMA_1'] > data['ATR_TS']) & (data['EMA_1_shifted'] <= data['ATR_TS_shifted'])
    return atr_buy_column, atr_sell_column

def calculate_buy_sell_signals(ticker_data):
    atr_buy_column, atr_sell_column = calculate_atr_buy_sell_signal(ticker_data)
    rsi_buy_column = calculate_rsi_buy_signal(ticker_data)
    stochastic_buy_column = calculate_stochastic_buy_signal(ticker_data)
    
    return [
        atr_buy_column,
        rsi_buy_column,
        stochastic_buy_column,
    ], atr_sell_column

def get_buy_columns_combinations(buy_columns):
    atr_buy_signal = "atrBuySignal"
    all_combinations = [[atr_buy_signal]]

    buy_columns = [col for col in buy_columns if col != atr_buy_signal]

    for r in range(1, len(buy_columns) + 1):
        for combo in combinations(buy_columns, r):
            combo = set(combo)
            combo.add(atr_buy_signal)
            combo = sorted(combo)

            all_combinations.append(combo)

    return all_combinations

def is_today_buy_stock(transactions: list, ticker_data: pd.DataFrame) -> bool:
    ticker_data_last = ticker_data.tail(1)  

    # if buy signal is generated today
    if transactions and transactions[-1] \
        and transactions[-1].buy_date.date() == ticker_data_last.index[0].date():
        return True
    
    return False

def is_today_exit_stock(ticker_data: pd.DataFrame) -> bool:
    ticker_data_last = ticker_data.tail(1)
    return any(ticker_data_last[app_params.ATR_SELL_COLUMN])

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
        1. It calls the `_open_long_position` function with the ticker name, buy columns combinations, the row, the capital, the open positions, and the index.
        2. It checks if the row contains a sell signal. If it does, it calls the `_close_long_position` function with the ticker name, the row, the open positions, the profit percentage till date, and the index.
        3. It iterates over the buy columns combinations and calculates the profit column name.
        4. It retrieves the profit percentage for the current row from the `profit_perc_till_date` dictionary.
        5. It assigns the profit percentage to the corresponding profit column in the row.
        6. It returns the processed row.
        """
        index = row.name
        _open_long_position(ticker_name, buy_columns_combinations, row, params.CAPITAL, open_positions, index)

        if row[sell_column]:
            _close_long_position(ticker_name, row, open_positions, profit_perc_till_date, index)
        
        for buy_cols_combination in buy_columns_combinations:
            profit_column = get_profit_column_name(buy_cols_combination)
            row[profit_column] = profit_perc_till_date.get(profit_column)
        
        return row

    df_with_profit_cols = df_with_profit_cols.apply(process_row, axis=1)

    return df_with_profit_cols

def _close_long_position(ticker_name, row, open_positions, profit_perc_till_date, index):
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

def _open_long_position(ticker_name, buy_columns_combinations, row, balance, open_positions, index):
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
    print()
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