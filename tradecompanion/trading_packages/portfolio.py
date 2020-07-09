# -------------------------------------------------------------------------- #
# Portfolio Management System module
# -------------------------------------------------------------------------- #
# Import Modules & Packages
import datetime
from dataclasses import dataclass


# -------------------------------------------------------------------------- #
# Class definition: will represent a portfolio of stocks
# -------------------------------------------------------------------------- #
@dataclass
class Portfolio(object):
    name: str
    open_date: datetime.date
    cash_value: float = 4000.0
    market_value: float = 0

    def __post_init__(self):
        self.total_value = self.market_value + self.cash_value

    def risk(self, price: float, atr: float, risk_per_trade: float,
             risk_ratio: float, stop_margin: float = 1.0):
        sizing = {'risk_per_share': stop_margin * atr}
        sizing['stop_price'] = price - sizing['risk_per_share']
        sizing['profit_per_share'] = risk_ratio * sizing['risk_per_share']
        sizing['shares_to_buy'] = round(self.total_value * risk_per_trade / sizing['risk_per_share'])
        sizing['target_price'] = price + sizing['profit_per_share']
        return sizing

    def cagr(self, value):
        pass  # TODO: Implement cumulative annual growth rate calculation

    def beta(self):
        pass  # TODO: Implement portfolio beta calculation


# -------------------------------------------------------------------------- #
# Class definition: will represent a position in the market
# -------------------------------------------------------------------------- #
@dataclass
class Position(object):
    fees = 4.95/1.3  # Commission fees in USD

    ticker: str
    nb_shares: int
    open_date: datetime.date
    close_date: datetime.date
    open_price: float
    stop_loss: float
    target_price: float
    close_price: float = 0.0
    status: str = 'Open'
    total_return: float = 0.0
    realized_pnl: float = 0.0

    def __post_init__(self):
        self.total_cost = self.open_price * self.nb_shares + Position.fees
        self.market_value = self.open_price * self.nb_shares

    def close_position(self, price, data_date):
        self.status = 'Close'
        self.close_date = data_date
        self.close_price = price
        self.total_return = price * self.nb_shares - Position.fees
        self.realized_pnl = self.total_return - self.total_cost
