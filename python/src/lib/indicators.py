import ta
import pandas as pd

def calculate_atr_trailing_stop(data, atr_sensitivity=2, atr_period=3):
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
    lowest_low = data['Low'].rolling(window=k_length).min()
    highest_high = data['High'].rolling(window=k_length).max()
    close = data['Close']
    
    # for rescaling the values from (-100 to 100) to (0 to 100)
    fast_k = ( (100 * (close - lowest_low) / (highest_high - lowest_low) ) + 100) * 0.5
    smooth_fast_k = ta.trend.sma_indicator(fast_k, window=k_smooth_period)
    fast_d = ta.trend.sma_indicator(smooth_fast_k, window=d_smooth_period)

    return smooth_fast_k, fast_d
