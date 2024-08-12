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
    env_file_path = os.path.join(project_root_dir, 'colab.env')
    load_dotenv(env_file_path)


if __name__ == "__main__":
    init_project()

# ============================ Business logic ==============================
import pandas as pd
import time
import logging
import builtins
from multiprocessing import Pool
import math
import argparse

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from lib.util.file_util import get_nifty_stock_names, create_output_csv
from finance.service import get_tickers_data
from strategy.service import get_best_strategy_stats
from indicator.service import calculate_stock_growth, calculate_buy_sell_signals
from indicator.service import get_buy_columns_combinations, calculate_atr_trailing_stop
from lib.util import date_util
import lib.params as app_params
from lib.util.dataframe_util import create_output_dataframes
from lib.models import OutputDataframeBuilder
from lib.util.email_utils import create_send_email


def init_log(suffix):
    log_file_name = os.path.join(os.getenv("OUTPUT_DIR"), "log", f"indicator_{suffix}.log")
    logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')
    builtins.logging = logging
    
    builtins.logging.info(f"Initializing log for suffix={suffix} log_file_name={log_file_name}")

def pre_populate_indicators(ticker_df):
    # Calculating ATR trailing stop loss
    atr_column = calculate_atr_trailing_stop(ticker_df)

def process_stocks(args):
    print("Start stock processing")

    backtest_start_date, backtest_end_date, ticker_counter, ticker_names, manual_favourite_stocks = args
    
    init_log(ticker_counter)
    builtins.logging.info("Start stock processing")
    
    tickers_data = get_tickers_data(backtest_start_date, backtest_end_date, ticker_names)

    df_profit = OutputDataframeBuilder.build()
    df_favourite = OutputDataframeBuilder.build()
    df_buy = OutputDataframeBuilder.build()
    df_exit = OutputDataframeBuilder.build()

    processed_count = 0
    # Iterate over each stock
    for ticker_name, ticker_data in tickers_data.items():
        try:
            # Remove .NS from ticker name
            if ticker_name.endswith(".NS"):
                ticker_name = ticker_name[:-3]

            builtins.logging.info(f"Start stock processing for ticker={ticker_name}")

            pre_populate_indicators(ticker_data)
            stock_growth = calculate_stock_growth(ticker_data, backtest_start_date, backtest_end_date)

            buy_columns, sell_column = calculate_buy_sell_signals(ticker_data)  
            buy_columns_combinations = get_buy_columns_combinations(buy_columns)

            args = (ticker_name, stock_growth, ticker_data, sell_column, buy_columns_combinations, backtest_start_date, backtest_end_date)
            strategy_stat, transactions = get_best_strategy_stats(args)
            
            args = (manual_favourite_stocks, ticker_name, ticker_data, strategy_stat, transactions, df_profit, df_favourite, df_buy, df_exit, backtest_start_date, backtest_end_date)
            df_profit, df_favourite, df_buy, df_exit = create_output_dataframes(args)

            processed_count += 1
            print(f"Process id={ticker_counter} Processed stock={ticker_name} Completed={processed_count}/{len(ticker_names)}")
                
        except Exception as e:
            print(f"Error occured in processing stock. ticker={ticker_name}. error={e}")
            builtins.logging.exception(f"Error occured in processing stock. ticker={ticker_name}. error={e}")
            
            traceback.print_exc()
    
    return df_profit, df_favourite, df_buy, df_exit


if __name__ == "__main__":

    # Set up argument parser
    parser = argparse.ArgumentParser(description="Stock analysis script")
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    args = parser.parse_args()

    os.environ['EXECUTION_MODE'] = app_params.EXECUTION_MODE_TEST if args.test else app_params.EXECUTION_MODE_NORMAL

    _start_time = time.time()
    init_log("main")
    backtest_start_date, backtest_end_date = date_util.get_backtest_start_end_date(lookback_years=3)

    # Check if running in test mode
    if args.test:
        print("Running in test mode")
        # Test mode configurations
        # Only for testing purpose
        # It should be one more than the actual date
        backtest_end_date = "2024-07-25"
        ticker_names = ["^NSEI", "PGEL.NS"]
    else:
        print("Running in normal mode")
        # Normal mode configurations
        ticker_names = get_nifty_stock_names("nifty_stock_names.csv")

    df_buy = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    df_exit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])

    df_manual_favourite_stocks = pd.read_csv(os.path.join(os.getenv("INPUT_DIR"), "manual_favourite.csv"))
    manual_favourite_stocks = set(df_manual_favourite_stocks['Stock'])

    page_size = app_params.TICKER_PAGE_SIZE
    params = []
    result_dataframes = []

    # Create actual argument for process_stocks
    for i in range(0, len(ticker_names), page_size):                    
        ticker_names_page = ticker_names[i:i+page_size]        
        params.append((backtest_start_date, 
                       backtest_end_date, 
                       math.ceil(i/page_size), 
                       ticker_names_page, 
                       manual_favourite_stocks))

    # Run process_stocks in parallel
    if args.test:
        result_dataframes.append(process_stocks(params[-1]))
    else:
        process_count = int(os.getenv(app_params.ENV_KEY_PROCESS_COUNT, app_params.DEFAULT_PROCESS_COUNT))
        print(f"Spawning {process_count} child processes")
        builtins.logging.info(f"Spawning {process_count} child processes")

        with Pool(process_count) as p:
            result_dataframes = p.map(process_stocks, params)

    # Initialize empty DataFrames to concatenate results
    csv_profit_path, csv_favourite_path, csv_buy_path, csv_exit_path = create_output_csv(result_dataframes)
    
    if not args.test:
        try:
            create_send_email(csv_buy_path, csv_exit_path)
        except Exception as e:
            print(f"Error occured while sending email. error={e}")
            builtins.logging.exception(f"Error occured while sending email. error={e}")

    print(f"Time taken={round(time.time() - _start_time, 2)} seconds")