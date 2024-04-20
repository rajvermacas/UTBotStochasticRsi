class Transaction:
    def __init__(self, symbol, quantity, buy_price, buy_date):
        self.symbol = symbol
        self.quantity = quantity
        self.buy_price = buy_price
        self.buy_date = buy_date
        self.cost = self.quantity * self.buy_price

        self.sell_price = None
        self.sell_date = None
        self.profit = None
        self.duration = None
    
    def end(self, sell_price, sell_date):
        self.sell_price = sell_price
        self.sell_date = sell_date

        abs_profit = self.sell_price * self.quantity - self.cost
        self.profit = (self.sell_price * self.quantity - self.cost)/self.cost * 100
        self.duration = (self.sell_date - self.buy_date).days
        return abs_profit
    
    def get_profit(self):
        return self.profit

    def __str__(self):
        return f"Transaction(symbol={self.symbol}, quantity={self.quantity}, buy_price={self.buy_price}, buy_date={self.buy_date}, sell_price={self.sell_price}, sell_date={self.sell_date}, profit={self.profit}, duration={self.duration})"
