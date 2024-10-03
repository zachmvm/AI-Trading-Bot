from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from datetime import timedelta
from finbert_utils import estimate_sentiment

# Get API info from Alpaca
API_KEY = "PKDP4HPJB5G8E804ARD7"
API_SECRET = 'hpiLqRcUF0ak2w1YWirwqxYfXKYK522L9UBwpRfH'
BASE_URL = 'https://paper-api.alpaca.markets/v2'

# Store API credentials from Alpaca API
ALPACA_CREDS = {
    "API_KEY":API_KEY,
    "API_SECRET":API_SECRET,
    "PAPER": True
    
}

class MLTRADER(Strategy):
    def initialize(self, symbol:str='SPY', cash_at_risk:float=.5):
        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url="https://paper-api.alpaca.markets/v2", key_id=API_KEY, secret_key=API_SECRET)
    
    # Method to determine position sizing based on cash and stock price
    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price, 0)
        return cash, last_price, quantity 
    
    # Create method to get dates for stock data
    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d') 
    
    # Method to get sentiment analysis from news articles about the stock
    def get_sentiment(self):
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, start=three_days_prior, end=today)
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment 
    
    # Main trading logic to be executed on each iteration
    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()
        
        # If we have enough cash to trade, make buy/sell decisions
        if cash > last_price: 
            # Buy if sentiment is positive and confidence is very high (> 0.999)
            if sentiment == "positive" and probability > .999: 
                if self.last_trade == "sell": 
                    self.sell_all() 
                # Create and submit a buy order with a bracket (take profit/stop loss)
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "buy", 
                    type="bracket", 
                    take_profit_price=last_price*1.20, 
                    stop_loss_price=last_price*.95
                )
                self.submit_order(order) 
                self.last_trade = "buy"
            # Sell if sentiment is negative and confidence is very high (> 0.999)
            elif sentiment == "negative" and probability > .999: 
                if self.last_trade == "buy": 
                    self.sell_all() 
                # Create and submit a buy order with a bracket (take profit/stop loss)
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "sell", 
                    type="bracket", 
                    take_profit_price=last_price*.8, 
                    stop_loss_price=last_price*1.05
                )
                self.submit_order(order) 
                self.last_trade = "sell"

broker = Alpaca(ALPACA_CREDS)
# Define backtesting start and end dates
start_date = datetime(2023, 12, 10)
end_date = datetime(2023, 12, 31)


# Create an instance of the MLTRADER strategy with specified parameters
strategy = MLTRADER(name='mlstrat', broker=broker, parameters={"symbol": "SPY", "cash_at_risk": .5})
strategy.backtest(YahooDataBacktesting, start_date, end_date, parameters={"symbol": "SPY"})