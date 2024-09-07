import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

def get_stock_data(ticker, start_date, end_date):
    stock = yf.Ticker(ticker)
    data = stock.history(start=start_date, end=end_date)
    return data['Close']

def find_peaks_troughs(prices, prominence=1, distance=1):
    peaks, _ = find_peaks(prices, prominence=prominence, distance=distance)
    troughs, _ = find_peaks(-prices, prominence=prominence, distance=distance)
    
    # Combine peaks and troughs, sort by index
    extrema = sorted([(i, 'peak') for i in peaks] + [(i, 'trough') for i in troughs])
    
    filtered_extrema = []
    last_type = None
    
    for idx, ex_type in extrema:
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

def predict_movement(prices, peaks, troughs, current_price):
    last_extrema = max(peaks[-1], troughs[-1])
    last_price = prices.iloc[last_extrema]

    if current_price > last_price:
        print(f"Current price ({current_price:.2f}) is higher than the last extrema ({last_price:.2f})")
        prob_up, prob_down = analyze_price_movement(prices, peaks, troughs)
    else:
        print(f"Current price ({current_price:.2f}) is lower than or equal to the last extrema ({last_price:.2f})")
        prob_up, prob_down = analyze_price_movement(prices, troughs, peaks)

    print(f"Probability of price going up: {prob_up:.2%}")
    print(f"Probability of price going down: {prob_down:.2%}")

# Example usage
ticker = 'DIXON.NS'  # Apple Inc.
start_date = '2020-01-01'
end_date = '2023-12-31'  # Changed to a more recent end date

prices = get_stock_data(ticker, start_date, end_date)
# Calculate prominence as a percentage of the price range
price_range = prices.max() - prices.min()
prominence_percentage = 5  # 5% of the price range
prominence = price_range * (prominence_percentage / 100)

peaks, troughs = find_peaks_troughs(prices, prominence=prominence, distance=20)

plot_stock_with_peaks_troughs(prices, peaks, troughs)

print("Peaks:", prices.index[peaks].tolist())
print("Troughs:", prices.index[troughs].tolist())

# Get the latest price (you may need to adjust this to get the actual current price)
current_price = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]

predict_movement(prices, peaks, troughs, current_price)