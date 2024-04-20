# sourcery skip: for-append-to-extend, list-comprehension
import sys
import traceback
import pandas as pd
import concurrent.futures
import time
import logging
import builtins

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from lib.data_fetcher import get_tickers_data, get_nifty_500_stock_names
from lib.indicator_evaluation import get_transactions_summary, calculate_stock_growth, calculate_most_profitable_buy_combination
from lib.buy_sell import calculate_multiple_buy_sell_signals, get_buy_columns_combinations
from lib.indicators import calculate_atr_trailing_stop


from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def init_log():
    log_file_name = os.path.join(os.getenv("OUTPUT_DIR"), "indicator.log")
    logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')
    builtins.logging = logging

def get_backtest_start_end_date():
    backtest_start_date = "2020-01-01"
    backtest_end_date = "2050-01-01"
    return backtest_start_date, backtest_end_date

def create_profit_csv(df_profit, counter):
    profit_csv_filepath = os.path.join(
            os.getenv("OUTPUT_DIR"), f"stock_performanc{counter}.csv"
        )
    df_profit = df_profit.sort_values(by='Profit', ascending=False)
    df_profit.to_csv(profit_csv_filepath, index=False)
    print(f"Stocks profit csv created: {profit_csv_filepath}")

def create_threads_to_do_transactions(ticker_name, ticker_data, sell_column, buy_columns_combinations):
    ticker_data = ticker_data.copy(deep=True)
    futures = []
    
    for buy_combos in buy_columns_combinations:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures.append(
                executor.submit(
                    get_transactions_summary, ticker_name, ticker_data, buy_combos, sell_column
                )
            )
    
    print(f"Created threads to do transactions on all the buy columns combinations for ticker={ticker_name}")
    return futures

def pre_populate_indicators(ticker_df):
    # Calculating ATR trailing stop loss
    atr_column = calculate_atr_trailing_stop(ticker_df)

if __name__=="__main__":
    _start_time = time.time()
    init_log()
    backtest_start_date, backtest_end_date = get_backtest_start_end_date()

    ticker_names = ["DIXON.NS", "^NSEI", "SAKUMA.NS"]
    # ticker_names = get_nifty_500_stock_names()
    df_profit = pd.DataFrame(columns=['Stock', 'Stock Growth', 'Profit'])

    page_size = 50
    offset = 0
    for i in range(0, len(ticker_names), page_size):
        ticker_names_page = ticker_names[i:i+page_size]
        tickers_data = get_tickers_data(backtest_start_date, backtest_end_date, ticker_names_page)

        for ticker_name, ticker_data in tickers_data.items():
            try:
                pre_populate_indicators(ticker_data)
                stock_growth = calculate_stock_growth(ticker_data, backtest_start_date, backtest_end_date)
                buy_columns, sell_column = calculate_multiple_buy_sell_signals(ticker_data)  
                buy_columns_combinations = get_buy_columns_combinations(buy_columns)
                futures = create_threads_to_do_transactions(ticker_name, ticker_data, sell_column, buy_columns_combinations)
                df_profit = calculate_most_profitable_buy_combination(ticker_name, stock_growth, futures, df_profit)

            except Exception as e:
                print(f"Error occured in main thread. ticker={ticker_name}. error={e}")
                builtins.logging.exception(f"Error occured in main thread. ticker={ticker_name}. error={e}")
        
        # It will create mutiple intermediate csv along with a final csv with all the stocks profit
        create_profit_csv(df_profit, i) 
        print("Time taken: ", time.time() - _start_time)


