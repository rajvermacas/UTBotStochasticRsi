"""
Prerequisites: input/nifty_stock_names.csv
"""
# sourcery skip: for-append-to-extend, list-comprehension

# ============================ Project setup ================================
from dotenv import load_dotenv
import sys
import os


def init_project():
    project_src_dir = os.path.dirname(__file__)
    sys.path.append(project_src_dir)

    project_root_dir = os.path.dirname(project_src_dir)
    
    os.environ['ROOT_DIR'] = project_root_dir
    os.environ['OUTPUT_DIR'] = os.path.join(project_root_dir, 'output')
    os.environ['INPUT_DIR'] = os.path.join(project_root_dir, 'input')

    # Load environment variables from .env file
    load_dotenv()


if __name__ == "__main__":
    init_project()

# ============================ Business logic ==============================
import pandas as pd
import concurrent.futures
import time
import logging
import builtins
from multiprocessing import Pool
from lib.buy_sell import is_today_buy_stock, is_today_exit_stock
from datetime import datetime, timedelta


import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from lib.data_fetcher import get_tickers_data, get_nifty_stock_names, is_favourite_stock
from lib.indicator_evaluation import get_transactions_summary, calculate_stock_growth, calculate_most_profitable_buy_combination
from lib.buy_sell import calculate_multiple_buy_sell_signals, get_buy_columns_combinations
from lib.indicators import calculate_atr_trailing_stop
from lib.util import date_util, csv_util


def init_log(suffix):
    log_file_name = os.path.join(os.getenv("OUTPUT_DIR"), "log", f"indicator_{suffix}.log")
    logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')
    builtins.logging = logging
    
    builtins.logging.info(f"Initializing log for suffix={suffix} log_file_name={log_file_name}")

def create_threads_to_do_transactions(ticker_name, ticker_data, sell_column, buy_columns_combinations):
    ticker_data = ticker_data.copy(deep=True)
    futures = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        futures.extend(
            executor.submit(
                get_transactions_summary,
                ticker_name,
                ticker_data,
                buy_cols_combination,
                sell_column,
            )
            for buy_cols_combination in buy_columns_combinations
        )
    print(f"Created threads to do transactions on all the buy columns combinations for ticker={ticker_name}")
    return futures

def pre_populate_indicators(ticker_df):
    # Calculating ATR trailing stop loss
    atr_column = calculate_atr_trailing_stop(ticker_df)

def maximise_stocks_profit(args):
    print(f"Starting to maximise stocks profit...")

    backtest_start_date, backtest_end_date, ticker_counter, ticker_names, manual_favourite_stocks = args
    
    df_profit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit'])
    df_favourite = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit'])
    df_buy = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    df_exit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    
    init_log(ticker_counter)
    builtins.logging.info(f"Starting to maximise stocks profit...")
    
    tickers_data = get_tickers_data(backtest_start_date, backtest_end_date, ticker_names)

    # Iterate over each stock
    for ticker_name, ticker_data in tickers_data.items():
        try:
            builtins.logging.info(f"Starting to maximise stocks profit for ticker={ticker_name}")

            pre_populate_indicators(ticker_data)
            stock_growth = calculate_stock_growth(ticker_data, backtest_start_date, backtest_end_date)

            buy_columns, sell_column = calculate_multiple_buy_sell_signals(ticker_data)  
            buy_columns_combinations = get_buy_columns_combinations(buy_columns)

            ticker_profit = 0
            buy_price = 0
            sell_price = 0

            # Iterate from start to end date
            # With each iteration add one more row from the iterated date
            # Iterate over each date in the ticker_data
            for i in range(1, len(ticker_data) + 1):
                # Create a subset of the data up to the current date
                current_data = ticker_data.iloc[:i].copy()
                
                # Create threads and calculate transactions for the current subset
                # futures = create_threads_to_do_transactions(ticker_name, current_data, sell_column, buy_columns_combinations)
                current_best_stat = calculate_most_profitable_buy_combination(ticker_name, stock_growth, current_data, sell_column, buy_columns_combinations)

                if is_today_buy_stock(current_best_stat, current_data):
                    buy_price = current_data['Close'][-1]
                
                if is_today_exit_stock(current_best_stat, current_data):
                    sell_price = current_data['Close'][-1]
                    profit = sell_price - buy_price
                    ticker_profit += profit
                    
                    buy_price = 0
                    sell_price = 0

                
                # Log progress
                if i % 100 == 0 or i == len(ticker_data):
                    builtins.logging.info(f"Processed {i}/{len(ticker_data)} rows for {ticker_name}")
                    print(f"Processed {i}/{len(ticker_data)} rows for {ticker_name}")
                
                # You might want to do something with current_best_stat here,
                # such as storing it or comparing it with previous results

            futures = create_threads_to_do_transactions(ticker_name, ticker_data, sell_column, buy_columns_combinations)
            best_transactions_stat = calculate_most_profitable_buy_combination(ticker_name, stock_growth, futures)

            df_profit = pd.concat(
                [
                    df_profit, 
                    pd.DataFrame(best_transactions_stat, index=[0])
                ], 
                ignore_index=True
            )

            is_favourite = is_favourite_stock(best_transactions_stat, ticker_name, manual_favourite_stocks)

            if is_favourite:
                df_favourite = pd.concat(
                    [
                        df_favourite, 
                        pd.DataFrame([best_transactions_stat])
                    ], 
                    ignore_index=True
                )
          
                if is_today_buy_stock(best_transactions_stat, ticker_data):
                    df_buy = pd.concat(
                        [
                            df_buy, 
                            pd.DataFrame([best_transactions_stat])
                        ], 
                        ignore_index=True
                    )

                if is_today_exit_stock(best_transactions_stat, ticker_data):
                    df_exit = pd.concat(
                        [
                            df_exit, 
                            pd.DataFrame([best_transactions_stat])
                        ], 
                        ignore_index=True
                    )
                
        except Exception as e:
            print(f"Error occured in maximising stock profit. ticker={ticker_name}. error={e}")
            builtins.logging.exception(f"Error occured in main thread. ticker={ticker_name}. error={e}")
    
    return df_profit, df_favourite, df_buy, df_exit
  

if __name__ == "__main__":
    _start_time = time.time()
    init_log("main")
    backtest_start_date, backtest_end_date = date_util.get_backtest_start_end_date(lookback_years=1)
    
    # Only for testing purpose
    backtest_end_date = "2024-05-25"

    # Only for testing purpose
    ticker_names = ["ARTEMISMED.NS", "^NSEI"]
    # ticker_names = get_nifty_stock_names("nifty_stock_names.csv")

    df_buy = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    df_exit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])

    df_manual_favourite_stocks = pd.read_csv(os.path.join(os.getenv("INPUT_DIR"), "manual_favourite.csv"))
    manual_favourite_stocks = {stock for stock in df_manual_favourite_stocks['Stock']}

    page_size = 50
    params = []
    results = []
    for i in range(0, len(ticker_names), page_size):                    
        ticker_names_page = ticker_names[i:i+page_size]        
        params.append((backtest_start_date, backtest_end_date, i, ticker_names_page, manual_favourite_stocks))
        
        # Only for testing purpose
        results.append(maximise_stocks_profit(params[-1]))
    
    # with Pool(8) as p:
    #     results = p.map(maximise_stocks_profit, params)
    
    # Initialize empty DataFrames to concatenate results
    final_df_profit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    final_df_favourite = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    final_df_buy = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    final_df_exit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])

    # Concatenate results from all processes
    for df_profit, df_favourite, df_buy, df_exit in results:
        final_df_profit = pd.concat([final_df_profit, df_profit], ignore_index=True)
        final_df_favourite = pd.concat([final_df_favourite, df_favourite], ignore_index=True)
        final_df_buy = pd.concat([final_df_buy, df_buy], ignore_index=True)
        final_df_exit = pd.concat([final_df_exit, df_exit], ignore_index=True)
    
    csv_util.create_csv(final_df_profit, 'Profit', 'performance')
    csv_util.create_csv(final_df_favourite, 'Winrate', 'favourite')
    csv_util.create_csv(final_df_buy, 'Winrate', 'buy')
    csv_util.create_csv(final_df_exit, 'Winrate', 'exit')
    
    print("Time taken: ", round(time.time() - _start_time, 2))



