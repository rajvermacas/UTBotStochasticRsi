import pandas as pd

from strategy.service import is_favourite_stock
from indicator.service import is_today_buy_stock, is_today_exit_stock


def create_output_dataframes(args):
    ticker_name, ticker_data, strategy_stat, transactions, df_profit, df_favourite, df_buy, df_exit, backtest_start_date, backtest_end_date = args

    df_profit = pd.concat(
                [
                    df_profit, 
                    pd.DataFrame(strategy_stat, index=[0])
                ], 
                ignore_index=True
            )

    if is_favourite_stock(strategy_stat,
                          ticker_name):
        
        df_favourite = pd.concat(
                    [
                        df_favourite, 
                        pd.DataFrame([strategy_stat])
                    ], 
                    ignore_index=True
                )
          
        if is_today_buy_stock(transactions, ticker_data):
            df_buy = pd.concat(
                        [
                            df_buy, 
                            pd.DataFrame([strategy_stat])
                        ], 
                        ignore_index=True
                    )

        if is_today_exit_stock(ticker_data):
            df_exit = pd.concat(
                        [
                            df_exit, 
                            pd.DataFrame([strategy_stat])
                        ], 
                        ignore_index=True
                    )
            
    return df_profit, df_favourite, df_buy, df_exit