from dotenv import load_dotenv
import sys
import os
import traceback

def init_project():
    project_src_dir = os.path.join(r"C:\Users\mrina\Documents\Projects\UTBotStochasticRsi\python\src")
    sys.path.append(project_src_dir)

    project_root_dir = os.path.dirname(project_src_dir)
    
    os.environ['ROOT_DIR'] = project_root_dir
    os.environ['OUTPUT_DIR'] = os.path.join(project_root_dir, 'output')
    os.environ['INPUT_DIR'] = os.path.join(project_root_dir, 'input')

    # Load environment variables from .env file
    env_file_path = os.path.join(project_root_dir, 'colab.env')
    load_dotenv(env_file_path)

if __name__ == "__main__":
    init_project()

import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy import stats

from lib.util.file_util import get_nifty_stock_names
from lib.util import date_util
from finance.service import get_tickers_data

def get_stock_data(ticker, start_date, end_date):
    stock = yf.Ticker(ticker)
    data = stock.history(start=start_date, end=end_date)
    return data['Close']

def find_peaks_troughs(prices, prominence_percentage=1, distance_percentage=1):
    price_range = prices.max() - prices.min()
    prominence = price_range * (prominence_percentage / 100)
    distance = int(len(prices) * (distance_percentage / 100))

    if distance < 1:
        distance = 1

    # Find peaks
    peaks, _ = find_peaks(prices, prominence=prominence, distance=distance)
    
    # Find troughs by inverting the prices
    troughs, _ = find_peaks(-prices, prominence=prominence, distance=distance)
    
    # Combine peaks and troughs, sort by index
    extrema = sorted([(i, 'peak') for i in peaks] + [(i, 'trough') for i in troughs])
    
    filtered_extrema = []
    last_type = None
    
    for idx, ex_type in extrema:
        # Ensure we alternate between peaks and troughs
        if last_type is None or ex_type != last_type:
            filtered_extrema.append((idx, ex_type))
            last_type = ex_type
    
    # Separate filtered peaks and troughs
    filtered_peaks = [idx for idx, ex_type in filtered_extrema if ex_type == 'peak']
    filtered_troughs = [idx for idx, ex_type in filtered_extrema if ex_type == 'trough']
    
    return np.array(filtered_peaks), np.array(filtered_troughs)

def plot_stock_with_peaks_troughs(prices, peaks, troughs):
    plt.figure(figsize=(12, 6))
    plt.plot(prices.index, prices, label='Stock Price')
    plt.plot(prices.index[peaks], prices.iloc[peaks], "^", color='g', markersize=10, label='Peaks')
    plt.plot(prices.index[troughs], prices.iloc[troughs], "v", color='r', markersize=10, label='Troughs')
    plt.title('Stock Price with Peaks and Troughs')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    plt.show()

def analyze_price_movement(prices, peaks, troughs):
    up_count = 0
    down_count = 0
    total_count = len(peaks) + len(troughs)

    for idx in np.concatenate((peaks, troughs)):
        if idx + 1 < len(prices):
            if prices.iloc[idx + 1] > prices.iloc[idx]:
                up_count += 1
            else:
                down_count += 1

    prob_up = up_count / total_count
    prob_down = down_count / total_count

    return prob_up, prob_down

def calculate_average_movement(prices, peaks, troughs):
    percentages = []
    i, j = 0, 0  # Initialize pointers for peaks and troughs

    while i < len(peaks) and j < len(troughs):
        if peaks[i] < troughs[j]:
            # Valid peak to trough movement
            percentage = ((prices.iloc[troughs[j]] - prices.iloc[peaks[i]]) / prices.iloc[peaks[i]]) * 100
            percentages.append(percentage)
            i += 1  # Move to the next peak
        else:
            j += 1  # Move to the next trough if the current peak is not valid

    if not percentages:
        return 0  # Return 0 if no crashes were found

    average_percentage = np.median(percentages)
    
    return average_percentage, percentages

def predict_movement(prices, peaks, troughs, current_price):
    last_extrema = max(peaks[-1], troughs[-1])
    last_price = prices.iloc[last_extrema]

    median_movement, trimmed_mean_movement, median_percentage, trimmed_mean_percentage = calculate_average_movement(prices, peaks, troughs)

    if current_price > last_price:
        print(f"Current price ({current_price:.2f}) is higher than the last extrema ({last_price:.2f})")
        prob_up, prob_down = analyze_price_movement(prices, peaks, troughs)
        expected_movement_median = current_price * (1 + median_percentage / 100)
        expected_movement_trimmed = current_price * (1 + trimmed_mean_percentage / 100)
    else:
        print(f"Current price ({current_price:.2f}) is lower than or equal to the last extrema ({last_price:.2f})")
        prob_up, prob_down = analyze_price_movement(prices, troughs, peaks)
        expected_movement_median = current_price * (1 - median_percentage / 100)
        expected_movement_trimmed = current_price * (1 - trimmed_mean_percentage / 100)

    print(f"Probability of price going up: {prob_up:.2%}")
    print(f"Probability of price going down: {prob_down:.2%}")
    print(f"Median movement between peaks and troughs: {median_movement:.2f}")
    print(f"Trimmed mean movement between peaks and troughs: {trimmed_mean_movement:.2f}")
    print(f"Median percentage change: {median_percentage:.2%}")
    print(f"Trimmed mean percentage change: {trimmed_mean_percentage:.2%}")
    print(f"Expected price movement (median): {expected_movement_median:.2f}")
    print(f"Expected price movement (trimmed mean): {expected_movement_trimmed:.2f}")

if __name__ == "__main__":
    backtest_start_date, backtest_end_date = date_util.get_backtest_start_end_date(
        lookback_years=4
    )
    ticker_names = get_nifty_stock_names("nifty_stock_names.csv")

    tickers_data = get_tickers_data(backtest_start_date, backtest_end_date, ticker_names)

    results = {}
    for ticker in ticker_names:
        prices = tickers_data[ticker]['Close']
        
        # Calculate prominence as a percentage of the price range
        prominence_percentage = 5  # 5% of the price range
        distance_percentage = 2

        peaks, troughs = find_peaks_troughs(prices, prominence_percentage=5, distance_percentage=1)

        try:
            avg_percent, crash_percentages = calculate_average_movement(prices, peaks, troughs)
            results[ticker] = (avg_percent, peaks, troughs)
        except Exception as e:
            print(f"Error calculating average movement for {ticker}: {e}")

    # Print results
    for ticker, (avg_percent, peaks, troughs) in results.items():
        print(f"{ticker}: Avg movement percentage between peaks and troughs: {avg_percent:.2f}%")

    # Optional: You can also plot for a specific stock if needed
    # example_ticker = "MICEL.NS"
    # plot_stock_with_peaks_troughs(tickers_data[example_ticker]['Close'], results[example_ticker][1], results[example_ticker][2])

    # Plot graphs for all stocks
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    def plot_all_stocks(tickers_data, results, prominence_percentage, distance_percentage):
        pdf_filename = f'all_stocks_plots_prom{prominence_percentage}_dist{distance_percentage}.pdf'
        counter = 1
        while os.path.exists(pdf_filename):
            pdf_filename = f'all_stocks_plots_prom{prominence_percentage}_dist{distance_percentage}_{counter}.pdf'
            counter += 1
        
        print(f"Starting to plot all stocks and save to {pdf_filename}")
        with PdfPages(pdf_filename) as pdf:
            for ticker, (avg_percent, peaks, troughs) in results.items():
                print(f"Plotting stock: {ticker}")
                fig, ax = plt.subplots(figsize=(12, 6))
                prices = tickers_data[ticker]['Close']
                
                ax.plot(prices.index, prices, label='Price')
                ax.scatter(prices.index[peaks], prices.iloc[peaks], color='green', label='Peaks')
                ax.scatter(prices.index[troughs], prices.iloc[troughs], color='red', label='Troughs')
                
                ax.set_title(f'{ticker}: Avg movement {avg_percent:.2f}%')
                ax.set_xlabel('Date')
                ax.set_ylabel('Price')
                ax.legend()
                
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
                print(f"Finished plotting {ticker}")
        
        print(f"All stock plots saved to {pdf_filename}")

    # Call the function to plot all stocks
    print("Starting to plot all stocks")
    plot_all_stocks(tickers_data, results, prominence_percentage, distance_percentage)
    print("Finished plotting all stocks")

