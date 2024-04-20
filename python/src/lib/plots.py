import plotly.graph_objects as go
import ta
from plotly.subplots import make_subplots

from lib.indicators import calculate_stochastic


def plot_graph(data, ticker_name):
    # Create a candlestick chart
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                                         open=data['Open'],
                                         high=data['High'],
                                         low=data['Low'],
                                         close=data['Close']),
                          go.Scatter(x=data.index, y=data['ATR_TS'], mode='lines', name='ATR Trailing Stop', line=dict(color='purple'), opacity=0.35),
                          # go.Scatter(x=data.index[data['closeAboveATRBuySignal']], y=data['Close'][data['closeAboveATRBuySignal']] * 1.01, mode='text', name='Buy Signal', marker=dict(color='green', size=10), text="BUY", textposition="top center"),
                          # go.Scatter(x=data.index[data['sellSignal']], y=data['Close'][data['sellSignal']] * 0.99, mode='text', name='Sell Signal', marker=dict(color='red', size=10), text="SELL", textposition="bottom center")])
    ])

    # Customize the layout
    fig.update_layout(title=ticker_name,
                      xaxis_title="Date",
                      yaxis_title="Price",
                      xaxis_rangeslider_visible=False,
                    #   dragmode='pan',
                      yaxis_fixedrange=False)

    # # Generate Stochastic Oscillator and add it to a new pane below the main graph
    # # stoch_oscillator = ta.momentum.StochasticOscillator(data['Low'], data['High'], data['Close'], window=14, smooth_window=3)
    # # k = stoch_oscillator.stoch()
    # k, d = calculate_stochastic(data)

    # fig = make_subplots(rows=2, cols=1)
    # fig.add_trace(go.Scatter(x=data.index, y=k, mode='lines', name='Stochastic %K', line=dict(color='blue')), row=1, col=1)
    # fig.add_trace(go.Scatter(x=data.index, y=d, mode='lines', name='Stochastic %D', line=dict(color='orange')), row=1, col=1)

    # # Adjust layout to accommodate the new pane
    # fig.update_layout(xaxis2=dict(anchor="y2"), yaxis2=dict(domain=[0, 0.2], anchor="x2", title="Stochastic Oscillator"))
    # fig.update_layout(xaxis=dict(domain=[0, 1], anchor="y", title="Date"), yaxis=dict(domain=[0.3, 1], anchor="x", title="Price"))

    # # Show the plot
    fig.show()