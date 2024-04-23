"""
Prerequisites: input/favourable_stocks.csv
"""
# sourcery skip: for-append-to-extend, list-comprehension
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
from lib.email_utils import send_email_with_attachments, get_recipient_emails

from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def init_log():
    log_file_name = os.path.join(os.getenv("OUTPUT_DIR"), "indicator.log")
    logging.basicConfig(filename=log_file_name, level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')
    builtins.logging = logging

def get_backtest_start_end_date():    
    tomorrow_date = datetime.now() + timedelta(days=1)
    start_date = tomorrow_date - timedelta(days=365*4)

    backtest_start_date = start_date.strftime("%Y-%m-%d")
    backtest_end_date = tomorrow_date.strftime("%Y-%m-%d")

    # backtest_start_date = "2024-01-01"
    # backtest_end_date = "2024-04-03" # For backtesting add 1 day + the actual date
    return backtest_start_date, backtest_end_date

def today_date():
    return datetime.now().strftime("%Y-%m-%d")

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
    t_date = today_date()
    write_csv_path = os.path.join(os.getenv("OUTPUT_DIR"), f"Buy_{t_date}.csv")
    
    cols = df_buy.columns.tolist()
    cols.insert(0, cols.pop(cols.index('Date')))  # Move the 'Date' column to the first position
    df_buy = df_buy[cols]

    df_buy.loc[:, 'Stock'] = df_buy['Stock'].str.replace(r'\.NS$', '', regex=True)
    df_buy = df_buy.sort_values(by='Winrate', ascending=False)

    df_buy.to_csv(write_csv_path, index=False)
    print(f"Today buy stocks csv created: {write_csv_path}")
    return write_csv_path

def create_csv_today_exit_stocks(df_exit):
    t_date = today_date()
    write_csv_path = os.path.join(os.getenv("OUTPUT_DIR"), f"Exit_{t_date}.csv")
    
    cols = df_exit.columns.tolist()
    cols.insert(0, cols.pop(cols.index('Date')))  # Move the 'Date' column to the first position
    df_exit = df_exit[cols]

    df_exit.loc[:, 'Stock'] = df_exit['Stock'].str.replace(r'\.NS$', '', regex=True)
    df_exit = df_exit.sort_values(by='Winrate', ascending=False)

    df_exit.to_csv(write_csv_path, index=False)
    print(f"Today exit stocks csv created: {write_csv_path}")
    return write_csv_path

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
        
    buy_csv_path = create_csv_today_buy_stocks(df_buy)
    exit_csv_path = create_csv_today_exit_stocks(df_exit) 

    recipient_emails = get_recipient_emails()
    send_email_with_attachments(
        "UTBotStochasticRSI Buy/Sell Stocks", 
        """
        Hi Trader,
        
        - Please find 2 csv files attached: one for buy stocks and the other for exit stocks.
        - The stock selection is based on backtesting from Jan 2017 to Apr 2024 across all the nifty 1966 stocks.
        - The data in the attached csv files' columns is based on the last 4 years of backtesting.
        - Before taking a trade, please cross-check with UTBotStochasticRSI at https://in.tradingview.com/script/pyOJZFzk-UT-Bot-Stochastic-RSI/
        
        Thank you
        UTBotStochasticRSI Team
        """,
        recipient_emails, 
        [buy_csv_path, exit_csv_path]
    )

    print("Time taken: ", time.time() - _start_time)
