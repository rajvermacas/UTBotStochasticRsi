import yfinance as yf
import pandas as pd
import os


def get_nifty_50_stock_names():
    tickers = pd.read_html('https://ournifty.com/stock-list-in-nse-fo-futures-and-options.html')[0]
    tickers = tickers['SYMBOL'].to_list()
    tickers = [ticker + ".NS" for ticker in tickers]
    return tickers

def extract_ticker_dataframe(ticker_name, tickers_data, open="Open", high="High", low="Low", close="Close"):
    df = pd.DataFrame()
    df[open] = tickers_data[open][ticker_name]
    df[high] = tickers_data[high][ticker_name]
    df[low] = tickers_data[low][ticker_name]
    df[close] = tickers_data[close][ticker_name]
    return df

def get_tickers_data(start_date, end_date, ticker_names):            
    tickers_data = yf.download(ticker_names, start_date, end_date)

    flattened_dataframes = {}
    for ticker_name in ticker_names:
        try:
            # Extracting individual ticker_name data
            # For ref: https://docs.google.com/spreadsheets/d/1GsoLQFtNLMqcdSff3dGdLJidt4ldZC-wVKdTcfiAh1Y/edit#gid=0
            ticker_df = extract_ticker_dataframe(ticker_name, tickers_data)
            # If there are missing values in any of Open, High, Low, Close then drop the rows
            ticker_df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)            
            # Creating a new DataFrame for each ticker_name
            flattened_dataframes[ticker_name] = ticker_df

        except KeyError:
            print(f"Data for {ticker_name} not found.")
    
    return flattened_dataframes

# Step 1: Get the list of Nifty 500 stocks
# You can use nsepy library to fetch the list

def get_nifty_500_stock_names():
    csv_path = os.path.join(os.getenv("INPUT_DIR", r"C:\Users\mrina\cursor-projects\workdocs\Trade\python\input"), "nifty500.csv")
    df = pd.read_csv(csv_path)
    df['Symbol'] = df['Symbol']+".NS"
    return df.Symbol.to_list()

def get_favourable_stock_names():
    csv_path = os.path.join(os.getenv("INPUT_DIR", r"C:\Users\mrina\cursor-projects\workdocs\Trade\python\input"), "favourable_stocks.csv")
    df = pd.read_csv(csv_path)
    df['Stock'] = df['Stock']+".NS"
    return df.Stock.to_list()


if __name__=="__main__":
    ticker_names = get_nifty_500_stock_names()
    print(ticker_names)