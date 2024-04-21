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

def create_csv_today_buy_stocks(df_buy):
    _, today_date = get_backtest_start_end_date()
    write_csv_path = os.path.join(os.getenv("OUTPUT_DIR"), f"{today_date}_buy_stocks.csv")
    
    cols = df_buy.columns.tolist()
    cols.insert(0, cols.pop(cols.index('Date')))  # Move the 'Date' column to the first position
    df_buy = df_buy[cols]

    df_buy.loc[:, 'Stock'] = df_buy['Stock'].str.replace(r'\.NS$', '', regex=True)

    df_buy.to_csv(write_csv_path, index=False)
    print(f"Today buy stocks csv created: {write_csv_path}")

def create_csv_today_exit_stocks(df_exit):
    _, today_date = get_backtest_start_end_date()
    write_csv_path = os.path.join(os.getenv("OUTPUT_DIR"), f"{today_date}_exit_stocks.csv")
    
    cols = df_exit.columns.tolist()
    cols.insert(0, cols.pop(cols.index('Date')))  # Move the 'Date' column to the first position
    df_exit = df_exit[cols]

    df_exit.loc[:, 'Stock'] = df_exit['Stock'].str.replace(r'\.NS$', '', regex=True)

    df_exit.to_csv(write_csv_path, index=False)
    print(f"Today exit stocks csv created: {write_csv_path}")

def calculate_today_buy_stocks(best_transactions_stat, ticker_data):
    ticker_data = ticker_data.tail(1)    
    buy_stocks = []

    buy_columns = best_transactions_stat['BuyColumns'].split(',')

    if all(ticker_data[col].all() for col in buy_columns):
        buy_date = ticker_data.index[0]
        best_transactions_stat['Date'] = buy_date
        buy_stocks.append(best_transactions_stat)
        
    return buy_stocks

def calculate_today_exit_stocks(best_transactions_stat, ticker_data):
    ticker_data = ticker_data.tail(1)
    exit_stocks = []

    exit_columns = best_transactions_stat['SellColumn'].split(',')

    if any(ticker_data[col].any() for col in exit_columns):
        sell_date = ticker_data.index[0]
        best_transactions_stat['Date'] = sell_date
        exit_stocks.append(best_transactions_stat)
    
    return exit_stocks


if __name__=="__main__":
    _start_time = time.time()
    init_log()
    backtest_start_date, backtest_end_date = get_backtest_start_end_date()

    ticker_names = get_favourable_stock_names()
    df_profit = pd.DataFrame()
    df_buy = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    df_exit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])

    page_size = 50
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
                best_transactions_stat = calculate_most_profitable_buy_combination(ticker_name, stock_growth, futures)
                
                buy_stocks = calculate_today_buy_stocks(best_transactions_stat, ticker_data)
                df_buy = pd.concat(
                    [
                        df_buy, 
                        pd.DataFrame(buy_stocks)
                    ], 
                    ignore_index=True
                )

                exit_stocks = calculate_today_exit_stocks(best_transactions_stat, ticker_data)
                df_exit = pd.concat(
                    [
                        df_exit, 
                        pd.DataFrame(exit_stocks)
                    ], 
                    ignore_index=True
                )

            except Exception as e:
                print(f"Error occured in main thread. ticker={ticker_name}. error={e}")
                builtins.logging.exception(f"Error occured in main thread. ticker={ticker_name}. error={e}")
        
    create_csv_today_buy_stocks(df_buy)
    create_csv_today_exit_stocks(df_exit) 
    print("Time taken: ", time.time() - _start_time)


