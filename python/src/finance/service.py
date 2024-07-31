import yfinance as yf
import pandas as pd
import copy



class FinanceService:
    """FinanceService class to download and process stock data."""

    flattened_dataframes = {}

    @classmethod
    def _extract_ticker_dataframe(ticker_name, tickers_data, open="Open", high="High", low="Low", close="Close"):
        df = pd.DataFrame()
        df[open] = tickers_data[open][ticker_name]
        df[high] = tickers_data[high][ticker_name]
        df[low] = tickers_data[low][ticker_name]
        df[close] = tickers_data[close][ticker_name]
        return df
    
    @classmethod
    def get_tickers_data(cls, start_date, end_date, ticker_names):            
        tickers_data = yf.download(ticker_names, start_date, end_date)
        
        for ticker_name in ticker_names:
            try:
                # Extracting individual ticker_name data
                # For ref: https://docs.google.com/spreadsheets/d/1GsoLQFtNLMqcdSff3dGdLJidt4ldZC-wVKdTcfiAh1Y/edit#gid=0
                ticker_df = cls._extract_ticker_dataframe(ticker_name, tickers_data)

                # If there are missing values in any of Open, High, Low, Close then drop the rows
                ticker_df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)            

                # Creating a new DataFrame for each ticker_name
                cls.flattened_dataframes[ticker_name] = ticker_df

            except KeyError:
                print(f"Data for {ticker_name} not found.")
        
        return copy.deepcopy(cls.flattened_dataframes)
    
    def get_ticker_df(cls, ticker_name, start_date, end_date):
        df = cls.flattened_dataframes[ticker_name]
        return copy.deepcopy(df.loc[start_date:end_date])