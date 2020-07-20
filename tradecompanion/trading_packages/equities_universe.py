# -------------------------------------------------------------------------- #
# Equities Universe module
# -------------------------------------------------------------------------- #

# Import Modules & Packages
import datetime
import pandas as pd
import yfinance as yf
from pandas_datareader import data as pdr
from dataclasses import dataclass

# This method will override the original data reader method
yf.pdr_override()


# -------------------------------------------------------------------------- #
# Class definition: will represent a stock object
# -------------------------------------------------------------------------- #
@dataclass
class Stock(object):
    ticker: str
    start_date: datetime.date
    end_date: datetime.date

    def __post_init__(self):
        self.ohcl = from_yahoo(self.ticker, self.start_date,
                               self.end_date, r='1d')

        self.open = self.ohcl['Open']
        self.close = self.ohcl['Close']
        self.high = self.ohcl['High']
        self.low = self.ohcl['Low']
        self.volume = self.ohcl['Volume']

    def atr(self, data_date: datetime.date, window: int = 20) -> float:
        data_ind = self.ohcl.index.get_loc(data_date)
        start_ind = data_ind - (window - 1)
        high = self.high.iloc[start_ind:data_ind + 1]
        low = self.low.iloc[start_ind:data_ind + 1]
        prev_close = self.close.iloc[start_ind - 1:data_ind]

        high_low = high - low
        high_pc = abs(high - prev_close)
        low_pc = abs(low - prev_close)

        true_range = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1, skipna=False)
        true_range.dropna(inplace=True)
        atr = true_range.rolling(len(true_range)).mean()[-1]
        return atr

    def rolling_means(
            self, mean_type: str, data_ind: int, window: int = 20
    ):
        start_ind = data_ind - (window - 1)
        max_pc = self.high.iloc[start_ind:data_ind + 1].rolling(window).max()[-1]
        max_vol = self.volume.iloc[start_ind:data_ind + 1].rolling(window).max()[-1]
        rolling = {'max_pc': max_pc, 'max_vol': max_vol}
        return rolling[mean_type]

    def signal(self, data_date: datetime.date, window: int = 20, volume_margin: float = 1.5):
        try:
            data_ind = self.ohcl.index.get_loc(data_date)

            high = self.high.iloc[data_ind]
            max_pc = self.rolling_means('max_pc', data_ind - 1, window)
            volume = self.volume.iloc[data_ind]
            max_volume = volume_margin * self.rolling_means('max_vol', data_ind - 1, window)
            good_position = (high >= 0.99 * max_pc and volume > 0.99 * max_volume)
        except:
            good_position = False
        return good_position


# -------------------------------------------------------------------------- #
# Function to get stocks data from Yahoo! Finance
# -------------------------------------------------------------------------- #
def from_yahoo(tick: str, start_date: datetime.date,
               end_date: datetime.date = None, r: str = '1d') -> pd.DataFrame:
    ohcl = pdr.get_data_yahoo(tick, start=start_date,
                              end=end_date, interval=r)

    assert isinstance(ohcl, pd.DataFrame)
    return ohcl
