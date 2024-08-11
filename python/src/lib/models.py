import pandas as pd


class Transaction:
    def __init__(self, symbol, quantity, buy_price, buy_date, buy_cols):
        self.symbol = symbol
        self.quantity = quantity
        self.buy_price = buy_price
        self.buy_date = buy_date
        self.cost = self.quantity * self.buy_price
        self.buy_cols = buy_cols

        self.sell_price = None
        self.sell_date = None
        
        # Profit %
        self.profit_perc = None
        self.abs_profit = None
        self.duration = None
    
    def is_active(self):
        return self.sell_price is None
    
    def end(self, sell_price, sell_date):
        self.sell_price = sell_price
        self.sell_date = sell_date

        self.abs_profit = self.sell_price * self.quantity - self.cost
        self.profit_perc = round((self.sell_price * self.quantity - self.cost)/self.cost * 100, 2)
        self.duration = (self.sell_date - self.buy_date).days
        return self.abs_profit
    
    def __str__(self):
        return f"Transaction(symbol={self.symbol}, quantity={self.quantity}, " + \
            f"buy_price={self.buy_price},  sell_price={self.sell_price}, " + \
            f"buy_date={self.buy_date}, sell_date={self.sell_date}, " + \
            f"profit_perc={self.profit_perc}, duration={self.duration} bars, " + \
            f"buy_cols={self.buy_cols})"
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'buy_price': self.buy_price,
            'sell_price': self.sell_price,
            'buy_date': self.buy_date,
            'sell_date': self.sell_date,
            'profit_perc': self.profit_perc,
            'duration': self.duration,
            'buy_cols': self.buy_cols
        }

class StrategyStatBuilder:
    @staticmethod
    def build(ticker_name, date, stock_growth):
        # Profit, stock growth, winrate is in percentage
        return {
            'Stock': ticker_name,
            'Date': date,
            'Stock Growth': stock_growth,
            'Wins': 0,
            'Losses': 0,
            'Entries': 0,
            'Exits': 0,
            'Winrate': 0,
            'Profit': 0,
            'Profit/StockGrowth': 0,
        }

class OutputDataframeBuilder:
    @staticmethod
    def build():
        return pd.DataFrame(columns=['Date', 'Stock', 'Stock Growth', 'Profit', 'Winrate', 'Profit/StockGrowth', 'Wins', 'Losses', 'Entries', 'Exits'])