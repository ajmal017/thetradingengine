# -------------------------------------------------------------------------- #
# Main Project script (Trading Engine)
# -------------------------------------------------------------------------- #

# Import Modules & Packages
from datetime import date, timedelta
from trading_packages import equities_universe as eu
from trading_packages import portfolio as pf
import pandas as pd
import matplotlib.pyplot as plt

# Define variables and analysis parameters
start_trading_date = date(2010, 3, 2)
start_data_date = date(2009, 3, 2)
end_date = date.today()

risk_per_trade = 0.01  # % of portfolio value on each trade
risk_ratio = 5
cash_ratio = 0.01  # % of cash to maintain in the portfolio at all time

# -------------------------------------------------------------------------- #
# Initialize functions & engines
# -------------------------------------------------------------------------- #

# From Trading Universe, Select tickers to be added to equities_universe
market_universe = ["MSFT", "AAPL", "FB", "AMZN", "INTC", "CSCO", "VZ", "IBM", "QCOM"]

# Import OHCL data for equities_universe
stock_data = [eu.Stock(i, start_data_date, end_date) for i in market_universe]
equities = dict(zip(market_universe, stock_data))

# Initialize a portfolio object
my_portfolio = pf.Portfolio('Momo', start_trading_date, cash_value=4000)

# Initialize a trading log dictionary
my_log = {}

# Initialize a trading engine
date_index = stock_data[0].ohcl.index
ind = date_index.get_loc(start_trading_date)
date_array_full = date_index.date
date_array = date_array_full[ind:]
trading_engine = pd.DataFrame(
    index=date_array,
    data={'Portfolio cash value': my_portfolio.cash_value,
          'Portfolio market value': my_portfolio.market_value,
          'Portfolio total value': my_portfolio.total_value})

# -------------------------------------------------------------------------- #
# Start looping over the Trading Window
# -------------------------------------------------------------------------- #
# POSITION OPENING ACTION SCRIPT IS PERFORMED BEFORE MARKET OPEN
# POSITION CLOSING ACTION IS PERFORMED DURING MARKET OPEN

for i, data_date in enumerate(date_array):
    # Verify if any trade opportunity that is not already in our portfolio
    previous_date = date_array_full[i + ind - 1]
    actual_cash_ratio = my_portfolio.cash_value / my_portfolio.total_value
    if actual_cash_ratio > cash_ratio:
        tick = []
        vol = []
        for stock in equities.values():
            if stock.signal(previous_date, window=40) and stock.ticker not in my_log.keys():
                tick.append(stock.ticker)
                vol.append(stock.volume[previous_date])
        if len(tick) != 0:
            opportunities = pd.DataFrame(index=tick, columns=['Volume'], data=vol)
            # Sort all opportunities by Volume
            opportunities.sort_values(by='Volume', ascending=False, inplace=True)
            # For each opportunity, going from the best one, verify that we have enough cash to open it.
            # If enough cash, open the position. If not skip it until all opportunities have been taken.
            for opportunity in opportunities.index:
                close_price = equities[opportunity].close[previous_date]
                stock_atr = equities[opportunity].atr(data_date=previous_date)
                position_sizing = my_portfolio.risk(price=close_price, atr=stock_atr, stop_margin=3,
                                                    risk_per_trade=risk_per_trade, risk_ratio=risk_ratio)
                remaining_cash = my_portfolio.cash_value - position_sizing['shares_to_buy'] * close_price
                if remaining_cash / my_portfolio.total_value > cash_ratio:
                    my_log[opportunity] = pf.Position(ticker=opportunity, nb_shares=position_sizing['shares_to_buy'],
                                                      open_date=data_date, close_date=data_date,
                                                      open_price=equities[opportunity].open.loc[data_date],
                                                      stop_loss=position_sizing['stop_price'],
                                                      target_price=position_sizing['target_price'])
                    my_portfolio.cash_value -= my_log[opportunity].total_cost
                else:
                    break
        del tick, vol

    my_portfolio.market_value = 0

    # Loop over the trading log to see if we have to close a position
    if len(my_log) != 0:
        market_val = 0
        for position in my_log.values():
            low_price = equities[position.ticker].low[data_date]
            high_price = equities[position.ticker].high[data_date]
            close_price = equities[position.ticker].close[data_date]
            if position.status == 'Open':
                if position.stop_loss > low_price:
                    price = position.stop_loss
                    position.close_position(price, data_date)
                    my_portfolio.cash_value += position.realized_pnl
                elif position.target_price < high_price:
                    price = position.target_price
                    position.close_position(price, data_date)
                    my_portfolio.cash_value += position.realized_pnl
                else:
                    my_portfolio.market_value += close_price * position.nb_shares
    my_portfolio.total_value = my_portfolio.market_value + my_portfolio.cash_value
    trading_engine.loc[data_date, 'Portfolio cash value'] = my_portfolio.cash_value
    trading_engine.loc[data_date, 'Portfolio market value'] = my_portfolio.market_value
    trading_engine.loc[data_date, 'Portfolio total value'] = my_portfolio.total_value

plt.plot(trading_engine['Portfolio total value'], )
plt.show()
print(trading_engine)
