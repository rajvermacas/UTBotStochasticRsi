import os
import pandas as pd
from lib.util import date_util
from lib.models import OutputDataframeBuilder
from lib import params as app_params


def get_manual_favourite_stocks() -> set:
    # The result set will not contain .NS suffix
    try:
        df_manual_favourite_stocks = pd.read_csv(
            os.path.join(
                os.getenv("INPUT_DIR"), 
                app_params.FILE_NAME_MANUAL_FAVOURITE_STOCKS
            )
        )   
        return set(df_manual_favourite_stocks['Stock'])
    
    except FileNotFoundError as fault:
        print(f"Error occured while getting manual favourite stocks. error={fault}")
        return set()

def get_favourite_stocks() -> set:
    # The result set will contain .NS suffix
    try:
        csv_path = os.path.join(os.getenv("INPUT_DIR"), app_params.FILE_NAME_FAVOURITE_STOCKS)
        df = pd.read_csv(csv_path)
        df['Stock'] = df['Stock']+".NS"
        return set(df.Stock)

    except Exception as fault:
        print(f"Error occured while getting favourite stocks. error={fault}")
        raise

def get_nifty_stock_names(filename=None) -> list:
    # The result set will contain .NS suffix

    if filename is None:
        filename = "nifty500_stock_names.csv"

    # If manual_favourite_stocks is present
    # Then add it to the list of stocks
    manual_favourite_stocks = get_manual_favourite_stocks()
    manual_favourite_stocks = {stock+".NS" for stock in manual_favourite_stocks}

    # If favourite_stocks is present in the input folder
    # Then return the list of stocks from that file
    # else return the list of all nifty stocks
    if os.path.exists(os.path.join(os.getenv("INPUT_DIR"), app_params.FILE_NAME_FAVOURITE_STOCKS)):
        return list(manual_favourite_stocks.union(get_favourite_stocks()))
    
    else:
        csv_path = os.path.join(os.getenv("INPUT_DIR"), filename)
        df = pd.read_csv(csv_path)
        df['Symbol'] = df['Symbol']+".NS"

        return list(manual_favourite_stocks.union(set(df.Symbol)))

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

    csv_profit_path = create_csv(final_df_profit, 'Profit', 'performance')
    csv_favourite_path = create_csv(final_df_favourite, 'Winrate', 'favourite')
    csv_buy_path = create_csv(final_df_buy, 'Winrate', 'buy')
    csv_exit_path = create_csv(final_df_exit, 'Winrate', 'exit')

    return csv_profit_path, csv_favourite_path, csv_buy_path, csv_exit_path