"""
Prerequisites: input/nifty_stock_names.csv
"""
# sourcery skip: for-append-to-extend, list-comprehension
import sys
import traceback
import pandas as pd
import concurrent.futures
import time
import logging
import builtins
from multiprocessing import Pool

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from lib.data_fetcher import get_tickers_data, get_nifty_stock_names
from lib.indicator_evaluation import get_transactions_summary, calculate_stock_growth, calculate_most_profitable_buy_combination
from lib.buy_sell import calculate_multiple_buy_sell_signals, get_buy_columns_combinations
from lib.indicators import calculate_atr_trailing_stop


from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def init_log(suffix):
    log_file_name = os.path.join(os.getenv("OUTPUT_DIR"), f"indicator_{suffix}.log")
    logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')
    builtins.logging = logging

def get_backtest_start_end_date():
    backtest_start_date = "2017-01-01"
    backtest_end_date = "2050-01-01"
    return backtest_start_date, backtest_end_date

def create_profit_csv(df_profit, counter):
    profit_csv_filepath = os.path.join(
            os.getenv("OUTPUT_DIR"), f"stock_performance{counter}.csv"
        )
    df_profit = df_profit.sort_values(by='Profit', ascending=False)
    df_profit.to_csv(profit_csv_filepath, index=False)
    print(f"Stocks profit csv created: {profit_csv_filepath}")

def create_threads_to_do_transactions(ticker_name, ticker_data, sell_column, buy_columns_combinations):
    ticker_data = ticker_data.copy(deep=True)
    futures = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures.extend(
            executor.submit(
                get_transactions_summary,
                ticker_name,
                ticker_data,
                buy_combos,
                sell_column,
            )
            for buy_combos in buy_columns_combinations
        )
    print(f"Created threads to do transactions on all the buy columns combinations for ticker={ticker_name}")
    return futures

def pre_populate_indicators(ticker_df):
    # Calculating ATR trailing stop loss
    atr_column = calculate_atr_trailing_stop(ticker_df)

def maximise_stocks_profit(args):
    backtest_start_date, backtest_end_date, ticker_counter, ticker_names = args
    df_profit = pd.DataFrame(columns=['Stock', 'Stock Growth', 'Profit'])
    init_log(ticker_counter)
    
    tickers_data = get_tickers_data(backtest_start_date, backtest_end_date, ticker_names)

    for ticker_name, ticker_data in tickers_data.items():
        try:
            pre_populate_indicators(ticker_data)
            stock_growth = calculate_stock_growth(ticker_data, backtest_start_date, backtest_end_date)
            buy_columns, sell_column = calculate_multiple_buy_sell_signals(ticker_data)  
            buy_columns_combinations = get_buy_columns_combinations(buy_columns)
            futures = create_threads_to_do_transactions(ticker_name, ticker_data, sell_column, buy_columns_combinations)
            best_transactions_stat = calculate_most_profitable_buy_combination(ticker_name, stock_growth, futures)

            df_profit = pd.concat(
                    [
                        df_profit, 
                        pd.DataFrame(best_transactions_stat, index=[0])
                    ], 
                    ignore_index=True
                )
                
        except Exception as e:
            print(f"Error occured in maximising stock profit. ticker={ticker_name}. error={e}")
            builtins.logging.exception(f"Error occured in main thread. ticker={ticker_name}. error={e}")
        
        # It will create mutiple intermediate csv along with a final csv with all the stocks profit
    create_profit_csv(df_profit, ticker_counter)
    return df_profit

if __name__=="__main__":
    _start_time = time.time()
    init_log("main")
    backtest_start_date, backtest_end_date = get_backtest_start_end_date()

    # ticker_names = ["DIXON.NS", "^NSEI"]
    ticker_names = get_nifty_stock_names("nifty_stock_names.csv")

    page_size = 50
    params = []
    for i in range(0, len(ticker_names), page_size):                    
        ticker_names_page = ticker_names[i:i+page_size]        
        params.append((backtest_start_date, backtest_end_date, i, ticker_names_page))
    
    with Pool(8) as p:
        df_profit = p.map(maximise_stocks_profit, params)

    print("Time taken: ", round(time.time() - _start_time, 2))



