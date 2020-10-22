# -------------------------------------------------------------------------- #
# Portfolio Management System module
# -------------------------------------------------------------------------- #
# Import Modules & Packages
import datetime
from dataclasses import dataclass
import pandas as pd
import numpy as np


# -------------------------------------------------------------------------- #
# Class definition: will represent a portfolio of stocks
# -------------------------------------------------------------------------- #
@dataclass
class Portfolio(object):
    name: str
    open_date: datetime.date
    cash_value: float = 4000.0
    market_value: float = 0
    cagr_KPI: float = 0
    volatility_KPI: float = 0
    sharpe_KPI: float = 0
    sortino_KPI: float = 0

    def __post_init__(self):
        self.total_value = self.market_value + self.cash_value

    def risk(self, price: float, atr: float, risk_per_trade: float,
             risk_ratio: float, stop_margin: float = 1.0) -> pd.DataFrame:
        sizing = {'risk_per_share': stop_margin * atr}
        sizing['stop_price'] = price - sizing['risk_per_share']
        sizing['profit_per_share'] = risk_ratio * sizing['risk_per_share']
        sizing['shares_to_buy'] = round(self.total_value * risk_per_trade / sizing['risk_per_share'])
        sizing['target_price'] = price + sizing['profit_per_share']
        return sizing

    def beta(self):
        pass  # TODO: Implement portfolio beta calculation


# -------------------------------------------------------------------------- #
# Class definition: will represent a position in the market
# -------------------------------------------------------------------------- #
@dataclass
class Position(object):
    fees = 4.95 / 1.3  # Commission fees in USD

    ticker: str
    nb_shares: int
    open_date: datetime.date
    close_date: datetime.date
    open_price: float
    stop_loss: float
    target_price: float
    market_value: float = 0.0
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
        self.market_value = price * self.nb_shares
        self.total_return = self.market_value - Position.fees
        self.realized_pnl = self.total_return - self.total_cost


# -------------------------------------------------------------------------- #
# Function to calculate some KPIs
# -------------------------------------------------------------------------- #

def cagr(daily_value: pd.Series) -> float:
    calc_df = pd.DataFrame()
    calc_df["daily_ret"] = daily_value.pct_change()
    calc_df["cum_return"] = (1 + calc_df["daily_ret"]).cumprod()
    n = len(calc_df) / 252
    return (calc_df["cum_return"][-1]) ** (1 / n) - 1


def volatility(daily_value: pd.Series) -> float:
    calc_df = daily_value.pct_change()
    vol = calc_df.std() * np.sqrt(252)
    return vol


def sharpe(daily_value: pd.Series, rf) -> float:
    sr = (cagr(daily_value) - rf) / volatility(daily_value)
    return sr


def sortino(daily_value: pd.Series, rf) -> float:
    chg = daily_value.pct_change()
    neg_vol = chg.where(chg < 0).std() * np.sqrt(252)
    sr = (cagr(daily_value) - rf) / neg_vol
    return sr
