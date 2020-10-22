# -------------------------------------------------------------------------- #
# Equities Universe module
# -------------------------------------------------------------------------- #

# Import Modules & Packages
import datetime
import pandas as pd
import yfinance as yf
from pandas_datareader import data as pdr
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup

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
        self.ohcl = from_yahoo(self.ticker, self.start_date, self.end_date, r='1d')

        self.open = self.ohcl['Open']
        self.close = self.ohcl['Close']
        self.high = self.ohcl['High']
        self.low = self.ohcl['Low']
        self.volume = self.ohcl['Volume']

    def date_window_index(self, data_date: datetime.date, window: int) -> tuple:
        data_ind = self.ohcl.index.get_loc(str(data_date))
        start_ind = data_ind - window + 1
        return data_ind, start_ind

    def atr(self, data_date: datetime.date, window: int = 14) -> float:
        data_ind, start_ind = self.date_window_index(data_date, window)
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

    def macd(self, data_date: datetime.date, short_p: int = 12, long_p: int = 26, mean_p: int = 9) -> tuple:
        data_ind, start_ind = self.date_window_index(data_date, 2 * long_p)
        close = self.close.iloc[start_ind:data_ind + 1]
        macd_fast = close.ewm(span=short_p, min_periods=short_p).mean()
        macd_slow = close.ewm(span=long_p, min_periods=long_p).mean()
        macd = macd_fast - macd_slow
        macd.dropna(inplace=True)
        macd_signal = macd.ewm(span=mean_p, min_periods=mean_p).mean()
        bullish = (macd[-1] > macd_signal[-1])
        return macd_signal, bullish

    def stochastics(self, data_date: datetime.date, window: int = 14):
        data_ind, start_ind = self.date_window_index(data_date, window)
        highest_high = self.high.iloc[start_ind:data_ind + 1].max()
        lowest_low = self.low.iloc[start_ind:data_ind + 1].min()
        current_close = self.close.iloc[data_ind]
        stochastic_oscillator = (current_close - lowest_low) / (highest_high - lowest_low) * 100
        return stochastic_oscillator

    def moving_avg(self, data_date: datetime.date, window: int = 50, avg_type: str = 'sma') -> float:
        data_ind, start_ind = self.date_window_index(data_date, window)
        close = self.close.iloc[start_ind:data_ind + 1]
        ma = {
            'sma': close.rolling(window=window).mean()[-1],
            'ema': close.ewm(span=window, min_periods=window).mean()[-1]
        }
        return ma[avg_type]

    def signal(self, data_date: datetime.date, window: int = 20, volume_margin: float = 1.5) -> bool:
        try:
            data_ind, start_ind = self.date_window_index(data_date, window=window)
            # -------------------------------------------------------------------------- #
            # Price action signal
            # -------------------------------------------------------------------------- #
            high = self.high.iloc[data_ind]
            max_pc = self.high.iloc[start_ind:data_ind].max()
            price_signal = (high >= 0.99 * max_pc)
            # -------------------------------------------------------------------------- #
            # Volume action signal
            # -------------------------------------------------------------------------- #
            volume = self.volume.iloc[data_ind]
            max_volume = volume_margin * self.volume.iloc[start_ind:data_ind].max()
            volume_signal = (volume > 0.99 * max_volume)
            # -------------------------------------------------------------------------- #
            # Overbought signal
            # -------------------------------------------------------------------------- #
            overbought_signal = self.stochastics(data_date=data_date) < 80
            # -------------------------------------------------------------------------- #
            # Trend signal
            # -------------------------------------------------------------------------- #
            mov_avg_50 = self.moving_avg(data_date=data_date, window=50, avg_type='sma')
            mov_avg_go_long = self.close.iloc[data_ind] > mov_avg_50
            # -------------------------------------------------------------------------- #
            # Position evaluation
            # -------------------------------------------------------------------------- #
            long_position = (price_signal
                             and volume_signal
                             and mov_avg_go_long
                             and overbought_signal)
        except:
            long_position = False
        return long_position


# -------------------------------------------------------------------------- #
# Function to get stocks data from Yahoo! Finance
# -------------------------------------------------------------------------- #
def from_yahoo(tick: str, start_date: datetime.date,
               end_date: datetime.date = None, r: str = '1d') -> pd.DataFrame:
    ohcl = pdr.get_data_yahoo(tick, start=start_date,
                              end=end_date, interval=r)

    assert isinstance(ohcl, pd.DataFrame)
    return ohcl


# -------------------------------------------------------------------------- #
# Function to web scrap tickers from wealthsimple halal portfolio
# -------------------------------------------------------------------------- #
def get_tick_wealth_simple() -> list:
    ws_url = 'https://help.wealthsimple.com/hc/en-ca/articles/115011786167-What-stocks-are-included-in-the-Halal-Investing-portfolio-'
    ws_tik = []
    r = requests.get(ws_url)
    data = r.text
    soup = BeautifulSoup(data, features='lxml')
    for listing in soup.find_all('tr'):
        for t in listing.find_all('td', attrs={'height': '21'}):
            ws_tik.append(t.text)
    ws_tik.pop(0)
    return ws_tik
