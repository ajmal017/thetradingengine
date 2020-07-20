# -------------------------------------------------------------------------- #
# Main Project script (Trading Engine)
# -------------------------------------------------------------------------- #
# Import Modules & Packages
from datetime import date, timedelta
from trading_packages import equities_universe as eu
from trading_packages import portfolio as pf
import pandas as pd
import matplotlib.pyplot as plt
from drawnow import drawnow

# Define variables and analysis parameters
start_trading_date = date(2015, 3, 4)
start_data_date = date(2014, 3, 2)
end_date = date.today()
# Strategy testing parameters
risk_per_trade = 0.01  # % of portfolio value on each trade
risk_ratio = 20
cash_ratio = 0.01  # % of cash to maintain in the portfolio at all time
initial_cash = 10000
signal_window = 10
stop_margin_multiple = 1
atr_window = 14
vol_marg = 1.25
# -------------------------------------------------------------------------- #
# Initialize functions & engines
# -------------------------------------------------------------------------- #
# From Trading Universe, Select tickers to be added to equities_universe
market_universe = ['L.TO', 'FTS.TO', 'PPl.TO', 'GIB-A.TO', 'FNV.TO', 'CSU.TO', 'GWO.TO', 'T.TO', 'NTR.TO', 'RCI-B.TO',
                   'WCN.TO', 'SLF.TO', 'ABX.TO', 'CNQ.TO', 'CP.TO', 'CM.TO', 'ATD-B.TO', 'MFC.TO', 'TRI.TO', 'SU.TO',
                   'BCE.TO', 'BMO.TO', 'TRP.TO', 'SHOP.TO', 'BAM-A.TO', 'CNR.TO', 'BNS.TO', 'ENB.TO', 'TD.TO', 'RY.TO']
# Import OHCL data for equities_universe
stock_data = [eu.Stock(i, start_data_date, end_date) for i in market_universe]
equities = dict(zip(market_universe, stock_data))
# Initialize a portfolio object
my_portfolio = pf.Portfolio('Momo', start_trading_date, cash_value=initial_cash)
# Initialize a trading log dictionary
my_log = []
# Initialize a trading engine
date_index = stock_data[0].ohcl.index
ind_1 = date_index.get_loc(start_trading_date)
date_array_full = date_index.date
date_array = date_array_full[ind_1:]
trading_engine = pd.DataFrame(
    index=date_array,
    data={'Portfolio cash value': None,
          'Portfolio market value': None,
          'Portfolio total value': None})


# Definition of a the figure plotting function
def make_fig():
    plt.plot(trading_engine['Portfolio total value'])


plt.ion()  # enable interactivity
fig = plt.figure()  # make a figure

# -------------------------------------------------------------------------- #
# Start looping over the Trading Window
# -------------------------------------------------------------------------- #
# POSITION OPENING ACTION SCRIPT IS PERFORMED BEFORE MARKET OPEN
# POSITION CLOSING ACTION IS PERFORMED DURING MARKET
for i, data_date in enumerate(date_array):
    previous_date = date_array_full[i + ind_1 - 1]
    actual_cash_ratio = my_portfolio.cash_value / my_portfolio.total_value
    # Get all open stock positions
    open_stocks = [stock.ticker for stock in my_log if stock.status == 'Open']
    # Verify that cash ratio condition is fulfilled
    if actual_cash_ratio > cash_ratio:
        tick = []
        vol = []
        # For all stocks in trading universe verify if we have signal and that we dont
        # have any open position for it
        for stock in equities.values():
            if stock.signal(previous_date, window=signal_window,
                            volume_margin=vol_marg) and stock.ticker not in open_stocks:
                tick.append(stock.ticker)
                vol.append(stock.volume[previous_date])
        # We create a data frame of good opportunities and we will sort them by a specific criteria.
        if len(tick) != 0:
            opportunities = pd.DataFrame(index=tick, columns=['Volume'], data=vol)
            # Sort all opportunities by Volume
            opportunities.sort_values(by='Volume', ascending=False, inplace=True)
            # For each opportunity, going from the best one, verify that we have enough cash to open it.
            # If enough cash, open the position. If not skip it until all opportunities have been verified.
            for opportunity in opportunities.index:
                prev_close_price = equities[opportunity].close[previous_date]
                open_price = equities[opportunity].open[data_date]
                stock_atr = equities[opportunity].atr(data_date=previous_date, window=atr_window)
                position_sizing = my_portfolio.risk(price=prev_close_price, atr=stock_atr,
                                                    stop_margin=stop_margin_multiple,
                                                    risk_per_trade=risk_per_trade, risk_ratio=risk_ratio)
                remaining_cash = my_portfolio.cash_value - position_sizing['shares_to_buy'] * prev_close_price
                if remaining_cash / my_portfolio.total_value > cash_ratio and prev_close_price <= open_price <= \
                        position_sizing['target_price']:
                    my_log.append(pf.Position(ticker=opportunity, nb_shares=position_sizing['shares_to_buy'],
                                              open_date=data_date, close_date=data_date,
                                              open_price=equities[opportunity].open.loc[data_date],
                                              stop_loss=position_sizing['stop_price'],
                                              target_price=position_sizing['target_price']))
                    my_portfolio.cash_value -= my_log[-1].total_cost
        del tick, vol
    # Loop over the trading log to see if we had to close a position during the trading time frame
    my_portfolio.market_value = 0
    if len(my_log) != 0:
        market_val = 0
        for position in my_log:
            if position.status == 'Open':
                if position.stop_loss > equities[position.ticker].low[data_date]:
                    price = position.stop_loss
                    position.close_position(price, data_date)
                    my_portfolio.cash_value += position.total_return
                    continue
                elif position.target_price < equities[position.ticker].high[data_date]:
                    price = position.target_price
                    position.close_position(price, data_date)
                    my_portfolio.cash_value += position.total_return
                    continue
                my_portfolio.market_value += equities[position.ticker].close[data_date] * position.nb_shares

    my_portfolio.total_value = my_portfolio.market_value + my_portfolio.cash_value
    # Trading engine data frame update
    trading_engine.loc[data_date, 'Portfolio cash value'] = my_portfolio.cash_value
    trading_engine.loc[data_date, 'Portfolio market value'] = my_portfolio.market_value
    trading_engine.loc[data_date, 'Portfolio total value'] = my_portfolio.total_value
    # Real-time figure drawing function
    drawnow(make_fig)
    plt.pause(0.001)
# -------------------------------------------------------------------------- #
# Performance Visualization
# -------------------------------------------------------------------------
my_log_df = pd.DataFrame({'ticker': [x.ticker for x in my_log], 'Nb of Shares': [x.nb_shares for x in my_log],
                          'Open Date': [x.open_date for x in my_log], 'Close_date': [x.close_date for x in my_log],
                          'Status': [x.status for x in my_log], 'Realized PnL': [x.realized_pnl for x in my_log],
                          'Open Price': [x.open_price for x in my_log], 'Stop Loss': [x.stop_loss for x in my_log],
                          'Target Price': [x.target_price for x in my_log],
                          'Close Price': [x.close_price for x in my_log]})
pass
