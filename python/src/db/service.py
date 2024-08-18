import yfinance as yf
import sqlite3
from datetime import datetime, timedelta
import pandas as pd


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
    nifty_stocks = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "HDFC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
        # ... Add all 50 Nifty stocks here
    ]

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
    end_date = datetime.now().date()

    for stock in nifty_stocks:
        print(f"Updating data for {stock}")
        latest_date = get_latest_date(cursor, stock)
        
        if latest_date:
            start_date = latest_date + timedelta(days=1)
        
        if start_date <= end_date:
            download_and_store_data(stock, start_date, end_date, cursor, conn)

    conn.close()
    print("Data update complete.")

def get_stock_data(symbol, from_date, to_date):
    conn = sqlite3.connect(r'C:\Users\mrina\Documents\Projects\UTBotStochasticRsi\python\nifty_stocks.db')
    cursor = conn.cursor()
    
    data = fetch_data(symbol, from_date, to_date, cursor, conn)
    
    conn.close()
    return data

if __name__ == "__main__":
    update_nifty_stocks_data()
    
    # Example usage of get_stock_data function
    start_date = datetime(2023, 1, 1).date()
    end_date = datetime(2023, 6, 1).date()
    data = get_stock_data("RELIANCE.NS", start_date, end_date)
    print(data)