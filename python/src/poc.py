import pandas as pd

# Read the CSV file
df = pd.read_csv(r'C:\Users\mrina\OneDrive\Documents\projects\UTBotStochasticRsi\python\output\dummy.csv', parse_dates=['Date'])

# List of profit indicator columns
# Profit columns by default are cumulated till date
profit_columns = [
    'profit_atrBuySignal',
    'profit_rsiBuySignal',
    'profit_stochasticBuySignal',
    'profit_rsiBuySignal_atrBuySignal',
    'profit_atrBuySignal_stochasticBuySignal',
    'profit_rsiBuySignal_stochasticBuySignal',
    'profit_rsiBuySignal_atrBuySignal_stochasticBuySignal'
]

# Corresponding signal columns
signal_columns = [
    ['atrBuySignal'],
    ['rsiBuySignal'],
    ['stochasticBuySignal'],
    ['rsiBuySignal', 'atrBuySignal'],
    ['atrBuySignal', 'stochasticBuySignal'],
    ['rsiBuySignal', 'stochasticBuySignal'],
    ['rsiBuySignal', 'atrBuySignal', 'stochasticBuySignal']
]

sell_column = 'atrSellSignal'

transaction = {
    'open_position': False,
    'buy_columns_combinations': None
}

def get_profit_column_name(signal_columns):
    return "profit_"+"_".join(signal_columns)

def calculate_summarised_profit(row):
    max_profit = 0
    best_signal_column_combination = None

    # Only take trade when not in trade already
    if not transaction['open_position']:
        for signal_col, profit_col in zip(signal_columns, profit_columns):
            if row[profit_col] > max_profit:
                max_profit = row[profit_col]
                best_signal_column_combination = signal_col

        # Check if the most profitable strategy is giving a buy signal
        if best_signal_column_combination and all(
            row[signal_col] for signal_col in best_signal_column_combination
        ):
            transaction['open_position'] = True
            transaction['profit_column'] = get_profit_column_name(best_signal_column_combination)
            print(f"Opening position. strategy={transaction['profit_column']} date of purchase={row['Date']}")

    # If there is a sell siganl, book profit
    if transaction['open_position'] and row[sell_column]:
        transaction['open_position'] = False

        result = row[transaction['profit_column']]
        transaction['buy_columns_combinations'] = None
        
        print(f"Exiting position. profit={result} date={row['Date']}\n")
        return result

    # If profit is not booked then return None
    return None

# Apply the function to create the summarised_profit column
df['summarised_profit'] = df.apply(calculate_summarised_profit, axis=1)

# Display the first few rows to verify
# print(df[['Date', 'summarised_profit'] + profit_columns + [col for sublist in signal_columns for col in (sublist if isinstance(sublist, list) else [sublist])]])

# Save the updated dataframe
df.to_csv(r'C:\Users\mrina\OneDrive\Documents\projects\UTBotStochasticRsi\python\output\NSE_profit_columns_updated.csv', index=False)