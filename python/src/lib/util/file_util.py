import os
import pandas as pd
from lib.util import date_util
from lib.models import OutputDataframeBuilder


def get_favourable_stock_names():
    csv_path = os.path.join(os.getenv("OUTPUT_DIR", r"C:\Users\mrina\cursor-projects\workdocs\Trade\python\output"), "favourable_stocks.csv")
    df = pd.read_csv(csv_path)
    df['Stock'] = df['Stock']+".NS"
    return df.Stock.to_list()

def get_nifty_stock_names(filename=None):
    if filename is None:
        filename = "nifty500_stock_names.csv"

    csv_path = os.path.join(os.getenv("INPUT_DIR", r"C:\Users\mrina\cursor-projects\workdocs\Trade\python\input"), filename)
    df = pd.read_csv(csv_path)
    df['Symbol'] = df['Symbol']+".NS"
    return df.Symbol.to_list()

def get_favourable_stock_names():
    csv_path = os.path.join(os.getenv("OUTPUT_DIR", r"C:\Users\mrina\cursor-projects\workdocs\Trade\python\output"), "favourable_stocks.csv")
    df = pd.read_csv(csv_path)
    df['Stock'] = df['Stock']+".NS"
    return df.Stock.to_list()

def get_nifty_50_stock_names():
    tickers = pd.read_html('https://ournifty.com/stock-list-in-nse-fo-futures-and-options.html')[0]
    tickers = tickers['SYMBOL'].to_list()
    tickers = [ticker + ".NS" for ticker in tickers]
    return tickers

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

def create_output_csv(results):
    final_df_profit = OutputDataframeBuilder.build()
    final_df_favourite = OutputDataframeBuilder.build()
    final_df_buy = OutputDataframeBuilder.build()
    final_df_exit = OutputDataframeBuilder.build()

    # Concatenate results from all processes
    for df_profit, df_favourite, df_buy, df_exit in results:
        final_df_profit = pd.concat([final_df_profit, df_profit], ignore_index=True)
        final_df_favourite = pd.concat([final_df_favourite, df_favourite], ignore_index=True)
        final_df_buy = pd.concat([final_df_buy, df_buy], ignore_index=True)
        final_df_exit = pd.concat([final_df_exit, df_exit], ignore_index=True)

    df_profit_path = create_csv(final_df_profit, 'Profit', 'performance')
    df_favourite_path = create_csv(final_df_favourite, 'Winrate', 'favourite')
    df_buy_path = create_csv(final_df_buy, 'Winrate', 'buy')
    df_exit_path = create_csv(final_df_exit, 'Winrate', 'exit')

    return df_profit_path, df_favourite_path, df_buy_path, df_exit_path