from dotenv import load_dotenv
import sys
import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def init_project():
    project_src_dir = os.path.join(r'C:\Users\mrina\Documents\Projects\UTBotStochasticRsi\python\src')
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


import yfinance as yf
import pandas as pd
import os
from db.service import get_max_stock_date, get_stocks_data, update_stocks_data


def extract_ticker_dataframe(ticker_name, tickers_data, open="Open", high="High", low="Low", close="Close"):
    print(f"Extracting data for ticker: {ticker_name}")
    try:
        df = tickers_data.loc[:, (slice(None), ticker_name)]
        df.columns = df.columns.droplevel(1)
        df = df[[open, high, low, close]]
        print(f"Successfully extracted data for {ticker_name}. Shape: {df.shape}")
        return df
    except KeyError as e:
        print(f"Error extracting data for {ticker_name}: {str(e)}")
    except Exception as e:
        print(f"Unexpected error occurred while extracting data for {ticker_name}: {str(e)}")
    return pd.DataFrame()

def get_tickers_data(start_date, end_date, ticker_names):
    # Convert start_date and end_date to datetime.date objects if they're strings
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    max_db_date = get_max_stock_date()
    
    if max_db_date is None or max_db_date < start_date:
        # No data in DB or all data needs to be downloaded
        download_start_date = start_date
    else:
        # Some data might be in DB
        download_start_date = max_db_date + timedelta(days=1)
    
    if download_start_date <= end_date:
        # Check if the difference is not just Saturday and Sunday
        days_difference = (end_date - download_start_date).days
        if days_difference > 2 or (days_difference > 0 and download_start_date.weekday() < 5):
            # Download missing data
            print(f"Downloading stock data from {download_start_date} to {end_date}...")
            tickers_data = yf.download(ticker_names, download_start_date, end_date)
            print(f"Downloaded stock data from {download_start_date} to {end_date}...")
        else:
            print("No need to download data: only weekend days in the date range.")
            tickers_data = None  # Empty DataFrame if no download is needed
        
        # Process all tickers at once
        flattened_dataframes = {}
        if tickers_data is not None:
            for ticker in ticker_names:
                try:
                    df = tickers_data.loc[:, (slice(None), ticker)]
                    df.columns = df.columns.droplevel(1)
                    df = df[['Open', 'High', 'Low', 'Close']]
                    df.dropna(inplace=True)
                    if not df.empty:
                        flattened_dataframes[ticker] = df
                    else:
                        print(f"DataFrame for {ticker} is empty after processing")
                except KeyError:
                    print(f"KeyError: Data for {ticker} not found in tickers_data")
                except Exception as e:
                    print(f"Unexpected error processing {ticker}: {str(e)}")
            print(f"Processed {len(flattened_dataframes)} tickers successfully")
            
            update_stocks_data(flattened_dataframes)
    
    # Fetch all required data from DB
    return get_stocks_data(start_date, end_date, ticker_names)


if __name__=="__main__":
    from lib.util.file_util import get_nifty_stock_names
    from lib.util import date_util
    import time

    _start_time = time.time()

    ticker_names = get_nifty_stock_names("nifty_stock_names.csv")
    backtest_start_date, backtest_end_date = date_util.get_backtest_start_end_date(
        lookback_years=1
    )
    tickers_data = get_tickers_data(backtest_start_date, backtest_end_date, ticker_names)
    print(tickers_data)

    print("Total time taken:", time.time() - _start_time)