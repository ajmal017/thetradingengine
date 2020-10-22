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
import csv
from pathlib import Path
from trading_packages.portfolio import Portfolio

# -------------------------------------------------------------------------- #
# Define data and trading dates
# -------------------------------------------------------------------------- #
start_trading_date = date(2015, 1, 6)
start_data_date = start_trading_date - timedelta(days=365)
offset = max(1, (start_data_date.weekday() + 6) % 7 - 3)
weekday_delta = timedelta(offset)
start_data_date -= weekday_delta
end_date = date.today()
# -------------------------------------------------------------------------- #
# Strategy back-testing parameters
# -------------------------------------------------------------------------- #
risk_per_trade = 0.01  # % of portfolio value on each trade
risk_ratio = 2
cash_ratio = 0.01  # % of cash to maintain in the portfolio at all time
initial_cash = 4000
signal_window = 10
stop_margin_multiple = 1
atr_window = 14
vol_marg = 1
# -------------------------------------------------------------------------- #
# Initialize functions & engines
# -------------------------------------------------------------------------- #
# Trading universe is a list of stocks tickers that are taken from a CSV file
ws_csv_data = Path(__file__).parent / "../data/WS_HALAL_PORTFOLIO.csv"
with ws_csv_data.open() as ws_data:
    ws_raw_data = list(csv.reader(ws_data, delimiter=','))
    ws_raw_data.pop(0)
market_universe = [t[0] for t in ws_raw_data]
# Import OHCL data for equities_universe
stock_data = [eu.Stock(i, start_data_date, end_date) for i in market_universe]
equities = dict(zip(market_universe, stock_data))
# Initialize a portfolio object
my_portfolio: Portfolio = pf.Portfolio('Momo', start_trading_date, cash_value=initial_cash)
# Initialize a trading log dictionary
my_log = []
# Initialize a trading engine
date_index = stock_data[0].ohcl.index
ind_1 = date_index.get_loc(str(start_trading_date))
date_array_full = date_index.date
date_array = date_array_full[ind_1:]
trading_engine = pd.DataFrame(index=date_array,
                              data={'Portfolio cash value': None,
                                    'Portfolio market value': None,
                                    'Portfolio total value': None})
# Initialize Win and Loss counters
nb_of_wins = 0
nb_of_losses = 0


# Definition of the figure plotting function
def make_fig():
    plt.plot(trading_engine['Portfolio total value'])
    plt.grid(axis='both')


plt.ion()  # enable interactivity
fig = plt.figure()  # make a figure

# -------------------------------------------------------------------------- #
# Start looping over the Trading Window
# -------------------------------------------------------------------------- #
for i, data_date in enumerate(date_array):
    previous_date = date_array_full[i + ind_1 - 1]
    # -------------------------------------------------------------------------- #
    # POSITION OPENING SCRIPT - PERFORMED BEFORE MARKET OPEN
    # -------------------------------------------------------------------------- #
    actual_cash_ratio = my_portfolio.cash_value / my_portfolio.total_value
    # Get all open stock positions
    open_stocks = [stock.ticker for stock in my_log if stock.status == 'Open']
    # Verify if cash ratio condition is fulfilled and that we can afford to open a position
    if actual_cash_ratio > cash_ratio:
        tick = []
        vol = []
        # For every stock in market universe verify if good signal AND that we dont have any open position for it
        for stock in equities.values():
            if stock.ticker not in open_stocks:
                if stock.signal(previous_date, window=signal_window, volume_margin=vol_marg):
                    tick.append(stock.ticker)
                    vol.append(stock.volume[str(previous_date)])
        # We create a data frame of good opportunities and we sort them by a specific criteria.
        if len(tick) != 0:
            opportunities = pd.DataFrame(index=tick, columns=['Volume'], data=vol)
            # Sort all opportunities by Volume
            opportunities.sort_values(by='Volume', ascending=False, inplace=True)
            # For each opportunity, going from the best one, verify that we have enough cash to open it.
            # If enough cash, open the position. If not skip it until all opportunities have been verified.
            for opportunity in opportunities.index:
                prev_close_price = equities[opportunity].close[str(previous_date)]
                open_price = equities[opportunity].open[str(data_date)]
                stock_atr = equities[opportunity].atr(data_date=previous_date, window=atr_window)
                position_sizing = my_portfolio.risk(price=prev_close_price, atr=stock_atr,
                                                    stop_margin=stop_margin_multiple,
                                                    risk_per_trade=risk_per_trade, risk_ratio=risk_ratio)
                remaining_cash = my_portfolio.cash_value - position_sizing['shares_to_buy'] * prev_close_price
                actual_cash_ratio = remaining_cash / my_portfolio.total_value
                if actual_cash_ratio > cash_ratio and prev_close_price <= open_price <= position_sizing['target_price']:
                    my_log.append(pf.Position(ticker=opportunity, nb_shares=position_sizing['shares_to_buy'],
                                              open_date=data_date, close_date=data_date,
                                              open_price=equities[opportunity].open.loc[str(data_date)],
                                              stop_loss=position_sizing['stop_price'],
                                              target_price=position_sizing['target_price']))
                    my_portfolio.cash_value -= my_log[-1].total_cost
                    my_portfolio.market_value += my_log[-1].market_value
                    my_portfolio.total_value = my_portfolio.cash_value + my_portfolio.market_value
    # -------------------------------------------------------------------------- #
    # POSITION CLOSING SCRIPT AND PORTFOLIO VALUE UPDATE
    # PERFORMED AT THE END OF THE TRADING DAY
    # -------------------------------------------------------------------------- #
    my_portfolio.market_value = 0  # Initialize portfolio market value
    if len(my_log) != 0:
        # Loop over the trading log to see if we had to close a position on the previous trading period
        for position in my_log:
            if position.status == 'Open':
                if position.stop_loss > equities[position.ticker].low[str(data_date)]:
                    price = position.stop_loss
                    position.close_position(price, data_date)
                    my_portfolio.cash_value += position.total_return  # Update portfolio cash value
                    if position.realized_pnl < 0:
                        nb_of_losses += 1
                    else:
                        nb_of_wins += 1
                    continue
                elif position.target_price < equities[position.ticker].high[str(data_date)]:
                    price = position.target_price
                    position.close_position(price, data_date)
                    my_portfolio.cash_value += position.total_return  # Update portfolio cash value
                    if position.realized_pnl < 0:
                        nb_of_losses += 1
                    else:
                        nb_of_wins += 1
                    continue
                else:
                    position_close_price = equities[position.ticker].close[str(data_date)]
                    reference_ma = equities[position.ticker].moving_avg(data_date=data_date)
                    if position_close_price > reference_ma:
                        stock_atr = equities[position.ticker].atr(data_date=data_date, window=atr_window)
                        position.stop_loss = reference_ma - stock_atr
                        position.target_price = position.stop_loss * risk_ratio
                    # Update portfolio market value
                    my_portfolio.market_value += position_close_price * position.nb_shares
    # -------------------------------------------------------------------------- #
    # UPDATING PORTFOLIO VALUE AND TRADING ENGINE
    # -------------------------------------------------------------------------- #
    # Add a monthly contribution to the portfolio
    # if data_date.month is not previous_date.month:
    #    my_portfolio.cash_value += 150
    # Here we update the portfolio total value after all transactions are done
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
# ------------------------------------------------------------------------- #
my_log_df = pd.DataFrame({'ticker': [x.ticker for x in my_log],
                          'Nb of Shares': [x.nb_shares for x in my_log],
                          'Open Date': [x.open_date for x in my_log],
                          'Close_date': [x.close_date for x in my_log],
                          'Status': [x.status for x in my_log],
                          'Realized PnL': [x.realized_pnl for x in my_log],
                          'Open Price': [x.open_price for x in my_log],
                          'Stop Loss': [x.stop_loss for x in my_log],
                          'Target Price': [x.target_price for x in my_log],
                          'Close Price': [x.close_price for x in my_log]})
# Get some index data
spy_index = eu.Stock(ticker='SPY', start_date=start_trading_date, end_date=end_date)
# Calculate the P&L of the portfolio
pnl = my_portfolio.total_value - initial_cash
# Calculate the Cumulative Annualized Gross Return
my_portfolio.cagr_KPI = pf.cagr(daily_value=trading_engine['Portfolio total value'])
spy_index_cagr = pf.cagr(daily_value=spy_index.close)
# Calculate the volatility
my_portfolio.volatility_KPI = pf.volatility(daily_value=trading_engine['Portfolio total value'])
spy_index_volatility = pf.volatility(daily_value=spy_index.close)
# Calculate the Sharpe ratio
my_portfolio.sharpe_KPI = pf.sharpe(daily_value=trading_engine['Portfolio total value'], rf=0.025)
spy_index_sharpe = pf.sharpe(daily_value=spy_index.close, rf=0.025)
# Calculate the Sortino ratio
my_portfolio.sortino_KPI = pf.sortino(daily_value=trading_engine['Portfolio total value'], rf=0.025)
spy_index_sortino = pf.sortino(daily_value=spy_index.close, rf=0.025)
# Print portfolio performance report
print('The initial value of your portfolio was ${:,}'.format(initial_cash))
print('The actual value is now ${:,}\n'.format(my_portfolio.total_value))
if pnl >= 0:
    print('You made a profit of ${:,}\n'.format(pnl))
else:
    print('You had a loss of $({:,})\n'.format(abs(pnl)))
print('The CAGR of the SPY Index is {:.2%}'.format(spy_index_cagr))
print('The CAGR of my portfolio is {:.2%}\n'.format(my_portfolio.cagr_KPI))
print('The volatility of the SPY Index is {:.2%}'.format(spy_index_volatility))
print('The volatility of my portfolio is {:.2%}\n'.format(my_portfolio.volatility_KPI))
print('The Sharpe ratio of my portfolio is {:.2%}'.format(my_portfolio.sharpe_KPI))
print('The Sharpe ratio of the SPY Index is {:.2%}\n'.format(spy_index_sharpe))
print('The Sortino ratio of my portfolio is {:.2%}'.format(my_portfolio.sharpe_KPI))
print('The Sortino ratio of the SPY Index is {:.2%}\n'.format(spy_index_sortino))
pass
