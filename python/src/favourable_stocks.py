"""
Prerequisites: input/stock_performance.csv
"""
# ============================ Project setup ================================
from dotenv import load_dotenv
import sys
import os

def init_project():
    project_src_dir = os.path.dirname(__file__)
    sys.path.append(project_src_dir)

    project_root_dir = os.path.dirname(project_src_dir)
    
    os.environ['ROOT_DIR'] = project_root_dir
    os.environ['OUTPUT_DIR'] = os.path.join(project_root_dir, 'output')
    os.environ['INPUT_DIR'] = os.path.join(project_root_dir, 'input')

    # Load environment variables from .env file
    load_dotenv()


if __name__ == "__main__":
    init_project()

# ============================ Business logic ==============================
import pandas as pd
import glob


if __name__=="__main__":
    csv_dir = "stock_performance"
    csv_files_names = "stock_performance*.csv"

    csv_files = glob.glob(os.path.join(os.getenv("OUTPUT_DIR"), csv_dir, csv_files_names))

    df_list = [pd.read_csv(file) for file in csv_files]
    df = pd.concat(df_list, ignore_index=True)

    
    filtered_df = df[(df['Profit/StockGrowth'] > 0.7) & (df['Profit'] > 70) & (df['Winrate'] >= 60)]
    
    filtered_df.loc[:, 'Stock'] = filtered_df['Stock'].str.replace(r'\.NS$', '', regex=True)
    filtered_df = filtered_df.sort_values(by='Winrate', ascending=False)
    
    write_csv_path = os.path.join(os.getenv("OUTPUT_DIR"), "favourable_stocks.csv")
    filtered_df.to_csv(write_csv_path, index=False)

    print(f"Favourable stocks csv generated: {write_csv_path}")
