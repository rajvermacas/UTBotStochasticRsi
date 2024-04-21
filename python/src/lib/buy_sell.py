import pandas as pd
import ta
from itertools import combinations

from lib.indicators import calculate_stochastic


def calculate_rsi_buy_signal(data, rsi_period=14, ema_period=14):
    # todo
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
    sell_column = 'atrSellSignal'
    buy_signal_generated = False
    for i in range(len(data)):
        if data[sell_column][i] and buy_signal_generated:
            buy_signal_generated = False  # Reset buy signal flag after a sell signal
        if not buy_signal_generated and data[rsi_buy_column][i]:
            buy_signal_generated = True  # Set buy signal flag
        else:
            data[rsi_buy_column].iloc[i] = False  # Do not generate buy signal if already generated
    
    return rsi_buy_column

def calculate_stochastic_buy_signal(data):
    # todo
    # sourcery skip: inline-immediately-returned-variable
    # Calculate %K and %D
    k, d = calculate_stochastic(data)
    data['%K'] = k
    data['%D'] = d
    
    # stochasticBuySignal = %K > %D 
    # and %D < 60
    # and close is above ATR
    stochasticBuySignal = (data['%K'] > data['%D']) & (data['%D'] < 60) & (data['Close'] >= data['ATR_TS'])

    stochastic_buy_column = 'stochasticBuySignal'
    data[stochastic_buy_column] = stochasticBuySignal

    # Generate buy Signal only at the first buy signal after a sell signal
    sell_column = 'atrSellSignal'
    buy_signal_generated = False
    for i in range(len(data)):
        if data[sell_column][i] and buy_signal_generated:
            buy_signal_generated = False  # Reset buy signal flag after a sell signal
        if not buy_signal_generated and data[stochastic_buy_column][i]:
            buy_signal_generated = True  # Set buy signal flag
        else:
            data[stochastic_buy_column].iloc[i] = False  # Do not generate buy signal if already generated

    return stochastic_buy_column

def calculate_atr_buy_sell_signal(data):
    """
    Ensure this is called after ATR_TS is calculated
    """
    atr_buy_column = 'atrBuySignal'
    atr_sell_column = 'atrSellSignal'
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

def calculate_close_above_atr_signal(data):
    """
    Ensure this is called after ATR_TS is calculated
    """
    close_above_atr_buy_column = 'closeAboveATRBuySignal'
    # Detecting crossover: ATR_TS crosses over EMA
    data[close_above_atr_buy_column] = (data['Close'] >= data['ATR_TS'])
    return close_above_atr_buy_column

def calculate_multiple_buy_sell_signals(ticker_data):
    atr_buy_column, atr_sell_column = calculate_atr_buy_sell_signal(ticker_data)
    rsi_buy_column = calculate_rsi_buy_signal(ticker_data)
    stochastic_buy_column = calculate_stochastic_buy_signal(ticker_data)
    
    return [
        atr_buy_column,
        rsi_buy_column,
        stochastic_buy_column,
    ], atr_sell_column

def get_buy_columns_combinations(buy_columns):
    all_combinations = []

    for r in range(1, len(buy_columns) + 1):
        for combo in combinations(buy_columns, r):
            combo = set(combo)
            all_combinations.append(combo)

    return all_combinations

