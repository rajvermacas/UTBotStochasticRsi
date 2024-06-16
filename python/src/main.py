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


import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from lib.data_fetcher import get_tickers_data, get_nifty_stock_names
from lib.indicator_evaluation import get_transactions_summary, calculate_stock_growth, calculate_most_profitable_buy_combination
from lib.buy_sell import calculate_multiple_buy_sell_signals, get_buy_columns_combinations
from lib.indicators import calculate_atr_trailing_stop
from lib.util import date_util


def init_log(suffix):
    log_file_name = os.path.join(os.getenv("OUTPUT_DIR"), "log", f"indicator_{suffix}.log")
    logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')
    builtins.logging = logging

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
    print(f"Starting to maximise stocks profit...")
    backtest_start_date, backtest_end_date, ticker_counter, ticker_names = args
    
    df_profit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit'])
    df_favourite = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit'])
    df_buy = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    df_exit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    
    init_log(ticker_counter)
    
    tickers_data = get_tickers_data(backtest_start_date, backtest_end_date, ticker_names)

    # Iterate over each stock
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

            is_favourite_stock = is_favourite(best_transactions_stat)

            if is_favourite_stock:
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


def is_favourite(best_transactions_stat: dict):
    return (best_transactions_stat['Profit/StockGrowth'] > 0.7) \
        and (best_transactions_stat['Profit'] > 200) \
        and (best_transactions_stat['Winrate'] >= 60)

def is_today_buy_stock(best_transactions_stat: dict, ticker_data: pd.DataFrame) -> bool:
    ticker_data = ticker_data.tail(1)    
    buy_columns = best_transactions_stat['BuyColumns'].split(',')

    return all(ticker_data[col].all() for col in buy_columns)

def is_today_exit_stock(best_transactions_stat: dict, ticker_data: pd.DataFrame) -> bool:
    ticker_data = ticker_data.tail(1)
    exit_columns = best_transactions_stat['SellColumn'].split(',')

    return any(ticker_data[col].any() for col in exit_columns)

def create_csv(df_buy, sort_by, filename, ascending=False):
    t_date = date_util.today_date()
    write_csv_path = os.path.join(os.getenv("OUTPUT_DIR"), f"{filename}_{t_date}.csv")
    
    cols = df_buy.columns.tolist()
    cols.insert(0, cols.pop(cols.index('Date')))  # Move the 'Date' column to the first position
    df_buy = df_buy[cols]

    df_buy = df_buy.sort_values(by=sort_by, ascending=ascending)

    df_buy.to_csv(write_csv_path, index=False)
    print(f"CSV created: {write_csv_path}")
    return write_csv_path
  

if __name__=="__main__":
    _start_time = time.time()
    init_log("main")
    backtest_start_date, backtest_end_date = date_util.get_backtest_start_end_date(lookback_years=2)
    
    # Only for testing purpose
    # backtest_end_date = "2024-05-25"

    # Only for testing purpose
    # ticker_names = ["ARTEMISMED.NS", "^NSEI"]
    ticker_names = get_nifty_stock_names("nifty_stock_names.csv")

    df_buy = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])
    df_exit = pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth'])

    page_size = 50
    params = []
    results = []
    for i in range(0, len(ticker_names), page_size):                    
        ticker_names_page = ticker_names[i:i+page_size]        
        params.append((backtest_start_date, backtest_end_date, i, ticker_names_page))
        
        # Only for testing purpose
        # results.append(maximise_stocks_profit(params[-1]))
    
    with Pool(8) as p:
        results = p.map(maximise_stocks_profit, params)
    
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
    
    create_csv(final_df_profit, 'Profit', 'performance')
    create_csv(final_df_favourite, 'Winrate', 'favourite')
    create_csv(final_df_buy, 'Winrate', 'buy')
    create_csv(final_df_exit, 'Winrate', 'exit')
    
    print("Time taken: ", round(time.time() - _start_time, 2))



