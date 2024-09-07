# ========================== Project setup ================================
import os
import sys
def init_project():
    project_src_dir = r"C:\Users\mrina\Documents\Projects\UTBotStochasticRsi\python\src"
    sys.path.append(project_src_dir)

    project_root_dir = os.path.dirname(project_src_dir)
    
    os.environ['ROOT_DIR'] = project_root_dir
    os.environ['OUTPUT_DIR'] = os.path.join(project_root_dir, 'output')
    os.environ['INPUT_DIR'] = os.path.join(project_root_dir, 'input')


if __name__ == "__main__":
    init_project()

# ========================== Business logic ==============================
import yfinance as yf
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
from lib.util.file_util import get_nifty_stock_names
import time


def get_latest_date(cursor, symbol):
    cursor.execute("SELECT MAX(date) FROM stock_data WHERE symbol = ?", (symbol,))
    result = cursor.fetchone()[0]
    return datetime.strptime(result.split()[0], "%Y-%m-%d").date() if result else None

def download_and_store_data(symbol, start_date, end_date, cursor, conn):
    data = yf.download(symbol, start=start_date, end=end_date)

    if not data.empty:
        # Convert the index to datetime if it's not already
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        
        # Get the earliest date in the downloaded data
        earliest_date = data.index.min().date()
        
        # Check if this date already exists in the database
        cursor.execute("SELECT COUNT(*) FROM stock_data WHERE symbol = ? AND date = ?", 
                       (symbol, earliest_date.strftime("%Y-%m-%d %H:%M:%S")))
        count = cursor.fetchone()[0]
        
        if count > 0:
            # Data for this date already exists, so we'll filter out existing dates
            cursor.execute("SELECT MAX(date) FROM stock_data WHERE symbol = ?", (symbol,))
            last_date_in_db = cursor.fetchone()[0]
            if last_date_in_db:
                last_date_in_db = datetime.strptime(last_date_in_db.split()[0], "%Y-%m-%d").date()
                data = data[data.index.date > last_date_in_db]

    if not data.empty:
        data = data.reset_index()
        data['Symbol'] = symbol
        data = data.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        data = data[['date', 'Symbol', 'open', 'high', 'low', 'close', 'volume']]
        data.to_sql('stock_data', conn, if_exists='append', index=False)
        conn.commit()
    
    else:
        print(f"No new data available for {symbol} between {start_date} and {end_date}")

def fetch_data(symbol, from_date, to_date, cursor, conn):
    cursor.execute("""
    SELECT * FROM stock_data 
    WHERE symbol = ? AND date BETWEEN ? AND ?
    ORDER BY date
    """, (symbol, from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")))
    
    data = cursor.fetchall()
    if not data:
        download_and_store_data(symbol, from_date, to_date, cursor, conn)
        return fetch_data(symbol, from_date, to_date, cursor, conn)
    
    return pd.DataFrame(data, columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'volume'])

def update_nifty_stocks_data():
    nifty_stocks = get_nifty_stock_names("nifty_stock_names.csv")
    print("Number of stocks to process:", len(nifty_stocks))

    conn = sqlite3.connect(r'C:\Users\mrina\Documents\Projects\UTBotStochasticRsi\python\nifty_stocks.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock_data (
        date TEXT,
        symbol TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        PRIMARY KEY (date, symbol)
    )
    ''')

    start_date = datetime(2000, 1, 1).date()
    # Add todays'date + 1 more day so that today's date is included
    # Because yfinance doesn't include last date in the data
    end_date = datetime.now().date() + timedelta(days=1)

    for stock in nifty_stocks:
        try:
            print(f"Updating data for {stock}")
            latest_date = get_latest_date(cursor, stock)
            
            if latest_date:
                start_date = latest_date + timedelta(days=1)
            
            if start_date <= end_date:
                download_and_store_data(stock, start_date, end_date, cursor, conn)

        except Exception as e:
            print(f"Error updating data for {stock}: {e}")

    conn.close()
    print("Data update complete.")

def get_stock_data(symbol, from_date, to_date):
    conn = sqlite3.connect(r'C:\Users\mrina\Documents\Projects\UTBotStochasticRsi\python\nifty_stocks.db')
    cursor = conn.cursor()
    
    data = fetch_data(symbol, from_date, to_date, cursor, conn)
    
    conn.close()
    return data

def get_max_stock_date():
    print("Starting get_max_stock_date function")
    conn = sqlite3.connect(r'C:\Users\mrina\Documents\Projects\UTBotStochasticRsi\python\nifty_stocks.db')
    cursor = conn.cursor()
    
    try:
        print("Executing SQL query to fetch max date")
        cursor.execute("SELECT MAX(date) FROM stock_data")
        max_date = cursor.fetchone()[0]
        
        if max_date:
            print(f"Max date found: {max_date}")
            return datetime.strptime(max_date, '%Y-%m-%d').date()
        else:
            print("No max date found in the database")
            return None
    except Exception as e:
        print(f"Error fetching max stock date: {e}")
        return None
    finally:
        print("Closing database connection")
        conn.close()
        print("get_max_stock_date function completed")


def init_project():
    project_src_dir = r"C:\Users\mrina\Documents\Projects\UTBotStochasticRsi\python\src"
    sys.path.append(project_src_dir)

    project_root_dir = os.path.dirname(project_src_dir)
    
    os.environ['ROOT_DIR'] = project_root_dir
    os.environ['OUTPUT_DIR'] = os.path.join(project_root_dir, 'output')
    os.environ['INPUT_DIR'] = os.path.join(project_root_dir, 'input')



def get_stocks_data(start_date, end_date, ticker_names):
    start_time = time.time()

    conn = sqlite3.connect(r'C:\Users\mrina\Documents\Projects\UTBotStochasticRsi\python\nifty_stocks.db')
    
    query = f"""
    SELECT date, symbol, open, high, low, close
    FROM stock_data 
    WHERE symbol IN ({','.join(['?']*len(ticker_names))})
      AND date BETWEEN ? AND ?
    ORDER BY symbol, date
    """
    
    params = ticker_names + [start_date if isinstance(start_date, str) else start_date.strftime("%Y-%m-%d"),
                             end_date if isinstance(end_date, str) else end_date.strftime("%Y-%m-%d")]
    
    query_start_time = time.time()
    df = pd.read_sql_query(query, conn, params=params)
    query_end_time = time.time()
    conn.close()
    
    print(f"SQL query to get stocks data execution time: {query_end_time - query_start_time:.2f} seconds")
    
    # Reshape the dataframe into a dictionary of dataframes
    reshape_start_time = time.time()
    flattened_dataframes = {}
    for ticker in ticker_names:
        ticker_df = df[df['symbol'] == ticker].copy()

        if not ticker_df.empty:
            ticker_df.set_index('date', inplace=True)
            ticker_df = ticker_df[['open', 'high', 'low', 'close']]

            ticker_df.columns = ['Open', 'High', 'Low', 'Close']
            flattened_dataframes[ticker] = ticker_df
    
    reshape_end_time = time.time()
    
    print(f"Dataframe reshaping to flattened_dataframes time: {reshape_end_time - reshape_start_time:.2f} seconds")
    print(f"Total get_stocks_data function execution time: {time.time() - start_time:.2f} seconds")
    
    return flattened_dataframes

def update_stocks_data(flattened_dataframes):
    print("Starting update_stocks_data function")
    conn = sqlite3.connect(r'C:\Users\mrina\Documents\Projects\UTBotStochasticRsi\python\nifty_stocks.db')
    cursor = conn.cursor()
    
    total_records = 0
    for ticker, df in flattened_dataframes.items():
        df = df.reset_index()
        df['symbol'] = ticker
        df.columns = ['date', 'open', 'high', 'low', 'close', 'symbol']
        
        # Prepare data for insertion
        data = df.to_dict('records')
        
        # Use INSERT OR REPLACE to update existing records or insert new ones
        # Convert Timestamp to string for SQLite compatibility
        for item in data:
            item['date'] = item['date'].strftime('%Y-%m-%d')

        try:
            cursor.executemany("""
                INSERT OR REPLACE INTO stock_data (date, symbol, open, high, low, close)
                VALUES (:date, :symbol, :open, :high, :low, :close)
            """, data)
            total_records += len(data)
            print(f"Successfully inserted/updated {len(data)} records for {ticker}")
        except Exception as e:
            print(f"Error inserting data for {ticker}: {str(e)}")
    
    conn.commit()
    print(f"Total records processed: {total_records}")
    conn.close()
    print("Finished update_stocks_data")

    
if __name__ == "__main__":
    _start_time = time.time()
    init_project()
    
    update_nifty_stocks_data()
    
    # Example usage of get_stock_data function
    # start_date = datetime(2023, 1, 1).date()
    # end_date = datetime(2023, 6, 1).date()
    # data = get_stock_data("RELIANCE.NS", start_date, end_date)
    # print(data)

    print("Total time taken:", time.time() - _start_time)