import pandas as pd
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


if __name__=="__main__":
    read_csv_path = os.path.join(os.getenv("INPUT_DIR"), "stock_performance500.csv")
    write_csv_path = os.path.join(os.getenv("OUTPUT_DIR"), "favourable_stocks.csv")
    
    df = pd.read_csv(read_csv_path)    
    filtered_df = df[(df['Profit/StockGrowth'] > 0.7) & (df['Profit'] > 200) & (df['Winrate'] >= 50)]
    
    filtered_df.loc[:, 'Stock'] = filtered_df['Stock'].str.replace(r'\.NS$', '', regex=True)
    filtered_df = filtered_df.sort_values(by='Winrate', ascending=False)
    filtered_df.to_csv(write_csv_path, index=False)

    print(f"Favourable stocks csv generated: {write_csv_path}")
