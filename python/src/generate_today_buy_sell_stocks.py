# sourcery skip: for-append-to-extend, list-comprehension
import sys
import traceback
import pandas as pd
import concurrent.futures
import time
import logging
import builtins
from datetime import datetime, timedelta

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from lib.data_fetcher import get_tickers_data, get_favourable_stock_names
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
    current_date = datetime.now()
    one_month_ago = current_date - timedelta(days=365*4)

    backtest_start_date = one_month_ago.strftime("%Y-%m-%d")
    backtest_end_date = current_date.strftime("%Y-%m-%d")
    return backtest_start_date, backtest_end_date

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

def create_csv_today_buy_stocks(df_buy):
    _, today_date = get_backtest_start_end_date()
    write_csv_path = os.path.join(os.getenv("OUTPUT_DIR"), f"{today_date}_buy_stocks.csv")
    
    df_buy.to_csv(write_csv_path, index=False)
    print(f"Today buy stocks csv created: {write_csv_path}")

def create_csv_today_exit_stocks(df_exit):
    _, today_date = get_backtest_start_end_date()
    write_csv_path = os.path.join(os.getenv("OUTPUT_DIR"), f"{today_date}_exit_stocks.csv")
    
    df_exit.to_csv(write_csv_path, index=False)
    print(f"Today exit stocks csv created: {write_csv_path}")

def calculate_today_buy_stocks(df_buy, df_ref, ticker_data):
    ticker_data = ticker_data.tail(1)    
    buy_stocks = []

    for index, row in df_ref.iterrows():
        buy_columns = row['BuyColumns'].split(',')

        if all(ticker_data[col].all() for col in buy_columns):
            buy_stocks.append(row)
    
    df_buy = pd.concat(
        [
            df_buy, 
            pd.DataFrame(buy_stocks)
        ], 
        ignore_index=False
    )
    return df_buy

def calculate_today_exit_stocks(df_exit, df_ref, ticker_data):
    ticker_data = ticker_data.tail(1)
    exit_stocks = []

    for index, row in df_ref.iterrows():
        exit_columns = row['SellColumn'].split(',')

        if any(ticker_data[col].any() for col in exit_columns):
            exit_stocks.append(row)
    
    df_exit = pd.concat(
        [
            df_exit, 
            pd.DataFrame(exit_stocks)
        ], 
        ignore_index=False
    )
    return df_exit


if __name__=="__main__":
    _start_time = time.time()
    init_log()
    backtest_start_date, backtest_end_date = get_backtest_start_end_date()

    ticker_names = get_favourable_stock_names()
    df_profit = pd.DataFrame()
    df_buy = pd.DataFrame()
    df_exit = pd.DataFrame()

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
                df_buy = calculate_today_buy_stocks(df_buy, df_profit, ticker_data)
                df_exit = calculate_today_exit_stocks(df_exit, df_profit, ticker_data)

            except Exception as e:
                print(f"Error occured in main thread. ticker={ticker_name}. error={e}")
                builtins.logging.exception(f"Error occured in main thread. ticker={ticker_name}. error={e}")
        
    create_csv_today_buy_stocks(df_buy)
    create_csv_today_exit_stocks(df_exit) 
    print("Time taken: ", time.time() - _start_time)


