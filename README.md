# UTBotStochasticRsi
1. pip install yfinance==0.2.37 ta==0.11.0 pandas==2.2.2
2. Change .env file to point to your project directory absolute path
3. Create a folder named output in python folder
4. backtest_multiple_stocks generates a csv which is used by favourable_stocks.py
5. favourable_stocks.py generates a csv which is used by generate_today_buy_sell_stocks.py
6. logs are generated in output/indicator.log