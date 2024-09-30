import sqlite3
import dash
from dash import dcc, html
from dash import dash_table
import plotly.graph_objs as go
import pandas as pd
import ccxt
import pandas as pd
import datetime

# Function to fetch OHLC data from Binance (or another exchange using ccxt)
def get_ohlc_from_binance(symbol='BNB/USDT', timeframe='15m', limit=100):
    try:
        exchange = ccxt.binance()
        ohlc = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        ohlc_df = pd.DataFrame(ohlc, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        ohlc_df['timestamp'] = pd.to_datetime(ohlc_df['timestamp'], unit='ms')
        return ohlc_df
    except Exception as e:
        print(f"Error fetching OHLC data: {e}")
        return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])  # Return empty DataFrame

# Initialize the Dash app
app = dash.Dash(__name__)

# Function to fetch data from a specific bot's database
def fetch_data(query, db_file):
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Fetch trade history from the database for the selected bot
def get_trade_history(db_file):
    query = "SELECT * FROM trades ORDER BY timestamp DESC"
    return fetch_data(query, db_file)

# Fetch balance history for the selected bot
def get_balance_history(db_file):
    query = "SELECT * FROM balance_checks ORDER BY timestamp DESC"
    return fetch_data(query, db_file)

# Fetch errors from the database for the selected bot
def get_errors_log(db_file):
    query = "SELECT * FROM errors ORDER BY timestamp DESC"
    return fetch_data(query, db_file)

# Cumulative PnL calculation
def get_cumulative_pnl(trade_df):
    trade_df['cumulative_pnl'] = trade_df['profit'].cumsum()
    return trade_df

# Get today's date
today = datetime.date.today()

# Set default start date (e.g., 30 days ago) and end date (today)
default_start_date = (today - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
default_end_date = today.strftime('%Y-%m-%d')

# Define layout with a dropdown to select between bots or view both bots
app.layout = html.Div(children=[
    html.H1(children='Dynamic Trading Bots Dashboard'),

    dcc.DatePickerRange(
        id='date-picker-range',
        start_date=default_start_date,
        end_date=default_end_date
    ),

    # Dropdown to select between Bot 1, Bot 2, or both
    dcc.Dropdown(
        id='bot-selector',
        options=[
            {'label': 'Bot 1', 'value': 'bot1'},
            {'label': 'Bot 2', 'value': 'bot2'},
            {'label': 'Both Bots', 'value': 'both'}
        ],
        value='both',  # Default to viewing both bots
        clearable=False
    ),

    # PnL Over Time for the selected bot
    #dcc.Graph(id='pnl-graph'),

    # Current Balance for the selected bot
    #dcc.Graph(id='balance-graph'),

    # OHLC Graph with Entry/Exit Points (New OHLC graph)
    html.H2('OHLC Data with Trade Entries/Exits'),
    dcc.Graph(id='ohlc-graph'),  # Add OHLC graph here

    # Trade History Table for the selected bot
    html.H2('Trade History'),
    dash_table.DataTable(
        id='trade-table',
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'},
        page_size=10
    ),

    # Error Logs Table for the selected bot
    html.H2('Error Logs'),
    dash_table.DataTable(
        id='error-table',
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'},
        page_size=10
    )
])

# Callback to update the graphs and tables based on bot selection
@app.callback(
    [
        #dash.dependencies.Output('pnl-graph', 'figure'),
        #dash.dependencies.Output('balance-graph', 'figure'),
        dash.dependencies.Output('trade-table', 'data'),
        dash.dependencies.Output('trade-table', 'columns'),
        dash.dependencies.Output('error-table', 'data'),
        dash.dependencies.Output('error-table', 'columns'),
        dash.dependencies.Output('ohlc-graph', 'figure'),  # New OHLC graph output
    ],
    [dash.dependencies.Input('bot-selector', 'value')]
)
def update_dashboard(bot_selection):
    bot1_db = 'dynamic_trading_V1.db'
    bot2_db = 'dynamic_trading_V2.db'

    if bot_selection == 'bot1':
        trade_df = get_trade_history(bot1_db)
        balance_df = get_balance_history(bot1_db)
        error_df = get_errors_log(bot1_db)
        ohlc_df = get_ohlc_from_binance(symbol='BNB/USDC', timeframe='1h', limit=100)  # Fetch OHLC data from Binance

    elif bot_selection == 'bot2':
        trade_df = get_trade_history(bot2_db)
        balance_df = get_balance_history(bot2_db)
        error_df = get_errors_log(bot2_db)
        ohlc_df = get_ohlc_from_binance(symbol='BNB/USDC', timeframe='1h', limit=100)  # Example for Bot 2

    else:
        trade_df1 = get_trade_history(bot1_db)
        trade_df2 = get_trade_history(bot2_db)
        trade_df = pd.concat([trade_df1, trade_df2], keys=['Bot 1', 'Bot 2'], names=['Bot'])

        balance_df1 = get_balance_history(bot1_db)
        balance_df2 = get_balance_history(bot2_db)
        balance_df = pd.concat([balance_df1, balance_df2], keys=['Bot 1', 'Bot 2'], names=['Bot'])

        error_df1 = get_errors_log(bot1_db)
        error_df2 = get_errors_log(bot2_db)
        error_df = pd.concat([error_df1, error_df2], keys=['Bot 1', 'Bot 2'], names=['Bot'])

        # Fetch OHLC data for both bots
        ohlc_df = get_ohlc_from_binance(symbol='BNB/USDC', timeframe='1h', limit=100)

    # Ensure the correct column is used for entry and exit timestamps
    print(trade_df.columns)  # Print column names to check the correct names

    # If you don't have separate entry and exit timestamps, adjust here
    if 'entry_timestamp' in trade_df.columns and 'exit_timestamp' in trade_df.columns:
        entry_timestamp_col = 'entry_timestamp'
        exit_timestamp_col = 'exit_timestamp'
    else:
        entry_timestamp_col = 'timestamp'  # Use 'timestamp' as a fallback
        exit_timestamp_col = 'timestamp'   # Use 'timestamp' as a fallback

    # Handle missing price columns
    if 'entry_price' not in trade_df.columns:
        trade_df['entry_price'] = None  # Add a placeholder column
    if 'exit_price' not in trade_df.columns:
        trade_df['exit_price'] = None  # Add a placeholder column


    # Cumulative PnL calculation
    #pnl_df = get_cumulative_pnl(trade_df)
    #pnl_figure = {
    #    'data': [
    #        go.Scatter(
    #            x=pnl_df['timestamp'],
    #            y=pnl_df['cumulative_pnl'],
    #            mode='lines+markers',
    #            name='PnL Over Time'
    #        )
    #    ],
    #    'layout': go.Layout(
    #        title='Cumulative PnL Over Time',
    #        xaxis={'title': 'Timestamp'},
    #        yaxis={'title': 'Cumulative PnL (USDC)'}
    #    )
    #}

    # Balance Over Time
    #balance_figure = {
    #    'data': [
    #        go.Scatter(
    #            x=balance_df['timestamp'],
    #            y=balance_df['balance'],
    #            mode='lines+markers',
    #            name='USDC Balance'
    #        )
    #    ],
    #    'layout': go.Layout(
    #        title='USDC Balance Over Time',
    #        xaxis={'title': 'Timestamp'},
    #        yaxis={'title': 'Balance (USDC)'}
    #    )
    #}

    # OHLC chart with trade entry and exit points
    ohlc_figure = {
        'data': [
            go.Candlestick(
                x=ohlc_df['timestamp'],
                open=ohlc_df['open'],
                high=ohlc_df['high'],
                low=ohlc_df['low'],
                close=ohlc_df['close'],
                name='OHLC Data'
            ),
            go.Scatter(
                x=trade_df[entry_timestamp_col],  # Adjusted column name
                y=trade_df['entry_price'],        # Assuming 'entry_price' exists
                mode='markers',
                marker=dict(color='green', size=10, symbol='triangle-up'),
                name='Entry Price'
            ),
            go.Scatter(
                x=trade_df[exit_timestamp_col],   # Adjusted column name
                y=trade_df['exit_price'],         # Assuming 'exit_price' exists
                mode='markers',
                marker=dict(color='red', size=10, symbol='triangle-down'),
                name='Exit Price'
            )
        ],
        'layout': go.Layout(
            title='OHLC Data with Trade Entry/Exit Points',
            xaxis={'title': 'Timestamp'},
            yaxis={'title': 'Price'}
        )
    }

    # Trade Table
    trade_data = trade_df.reset_index(drop=True).to_dict('records')
    trade_columns = [{"name": i, "id": i} for i in trade_df.columns]

    # Error Logs Table
    error_data = error_df.reset_index(drop=True).to_dict('records')
    error_columns = [{"name": i, "id": i} for i in error_df.columns]

    return trade_data, trade_columns, error_data, error_columns, ohlc_figure  # Return OHLC figure

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
