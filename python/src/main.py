"""
Prerequisites: input/nifty_stock_names.csv
"""
# sourcery skip: for-append-to-extend, list-comprehension

# ============================ Project setup ================================
from dotenv import load_dotenv
import sys
import os
import traceback


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
import math


import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from lib.data_fetcher import get_tickers_data, get_nifty_stock_names, is_favourite_stock
from lib.indicator_evaluation import calculate_stock_growth, get_best_strategy_stats
from lib.buy_sell import calculate_buy_sell_signals, get_buy_columns_combinations
from lib.indicators import calculate_atr_trailing_stop
from lib.util import date_util, csv_util


def init_log(suffix):
    log_file_name = os.path.join(os.getenv("OUTPUT_DIR"), "log", f"indicator_{suffix}.log")
    logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')
    builtins.logging = logging
    
    builtins.logging.info(f"Initializing log for suffix={suffix} log_file_name={log_file_name}")

def pre_populate_indicators(ticker_df):
    # Calculating ATR trailing stop loss
    atr_column = calculate_atr_trailing_stop(ticker_df)

def process_stocks(args):
    print("Starting to maximise stocks profit...")

    backtest_start_date, backtest_end_date, ticker_counter, ticker_names, manual_favourite_stocks = args
    
    init_log(ticker_counter)
    builtins.logging.info("Starting to maximise stocks profit...")
    
    tickers_data = get_tickers_data(backtest_start_date, backtest_end_date, ticker_names)

    df_profit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit'])
    df_favourite = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit'])
    df_buy = pd.DataFrame(columns=['Date', 'ticker_name', 'stock_growth', 'total_profit', 'winrate', 'total_profit/stock_growth'])
    df_exit = pd.DataFrame(columns=['Date', 'ticker_name', 'stock_growth', 'total_profit', 'winrate', 'total_profit/stock_growth'])

    processed_count = 0
    # Iterate over each stock
    for ticker_name, ticker_data in tickers_data.items():
        try:
            builtins.logging.info(f"Starting to maximise stocks profit for ticker={ticker_name}")

            pre_populate_indicators(ticker_data)
            stock_growth = calculate_stock_growth(ticker_data, backtest_start_date, backtest_end_date)

            buy_columns, sell_column = calculate_buy_sell_signals(ticker_data)  
            buy_columns_combinations = get_buy_columns_combinations(buy_columns)

            best_transactions_stat = get_best_strategy_stats(ticker_name, stock_growth, ticker_data, sell_column, buy_columns_combinations)
            
            args = (manual_favourite_stocks, ticker_name, ticker_data, best_transactions_stat, df_profit, df_favourite, df_buy, df_exit)
            df_profit, df_favourite, df_buy, df_exit = create_output_dataframes(args)

            processed_count += 1
            print(f"Process id={ticker_counter} Processed stock={ticker_name}. Completed={processed_count}/{len(ticker_names)}")
                
        except Exception as e:
            print(f"Error occured in maximising stock profit. ticker={ticker_name}. error={e}")
            builtins.logging.exception(f"Error occured in main thread. ticker={ticker_name}. error={e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()

            # Print the exception
            print("Exception type:", exc_type)
            print("Exception value:", exc_value)

            # Print the traceback
            print("Traceback:")
            traceback.print_tb(exc_traceback)
    
    return df_profit, df_favourite, df_buy, df_exit

def create_output_dataframes(args):
    manual_favourite_stocks, ticker_name, ticker_data, best_transactions_stat, df_profit, df_favourite, df_buy, df_exit = args

    best_transactions_stat.pop('open_position', None)
    best_transactions_stat.pop('profit_column', None)

    profit_transaction_stat = {k:v for k,v in best_transactions_stat.items() if k not in ['BuyColumns', 'SellColumn', 'TradeHistory', 'BuyDate']}

    df_profit = pd.concat(
                [
                    df_profit, 
                    pd.DataFrame(profit_transaction_stat, index=[0])
                ], 
                ignore_index=True
            )

    if is_favourite_stock(best_transactions_stat, ticker_name, manual_favourite_stocks):
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
            
    return df_profit, df_favourite, df_buy, df_exit
  

def create_output_csv(results):
    final_df_profit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth', 'Wins', 'Losses', 'Entries', 'Exits'])
    final_df_favourite = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth', 'Wins', 'Losses', 'Entries', 'Exits'])
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

if __name__ == "__main__":
    _start_time = time.time()
    init_log("main")
    backtest_start_date, backtest_end_date = date_util.get_backtest_start_end_date(lookback_years=1)

    # Only for testing purpose
    # backtest_end_date = "2024-05-25"

    # Only for testing purpose
    ticker_names = ["DIXON.NS", "^NSEI"]
    # ticker_names = get_nifty_stock_names("nifty_stock_names.csv")

    df_buy = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    df_exit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])

    df_manual_favourite_stocks = pd.read_csv(os.path.join(os.getenv("INPUT_DIR"), "manual_favourite.csv"))
    manual_favourite_stocks = set(df_manual_favourite_stocks['Stock'])

    page_size = 50
    params = []
    results = []
    for i in range(0, len(ticker_names), page_size):                    
        ticker_names_page = ticker_names[i:i+page_size]        
        params.append((backtest_start_date, backtest_end_date, math.ceil(i/50), ticker_names_page, manual_favourite_stocks))

        # Only for testing purpose
        results.append(process_stocks(params[-1]))

    # with Pool(8) as p:
    #     results = p.map(process_stocks, params)

    # Initialize empty DataFrames to concatenate results
    create_output_csv(results)

    print("Time taken: ", round(time.time() - _start_time, 2))



