from lib.util import date_util
import os



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