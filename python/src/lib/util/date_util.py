from datetime import datetime, timedelta


def today_date():
    return datetime.now().strftime("%Y-%m-%d")

def get_backtest_start_end_date(lookback_years=1):    
    tomorrow_date = datetime.now() + timedelta(days=1)
    start_date = tomorrow_date - timedelta(days=int(365*lookback_years))

    backtest_start_date = start_date.strftime("%Y-%m-%d")
    backtest_end_date = tomorrow_date.strftime("%Y-%m-%d")

    # backtest_start_date = "2024-01-01"
    # backtest_end_date = "2024-04-03" # For backtesting add 1 day + the actual date
    return backtest_start_date, backtest_end_date