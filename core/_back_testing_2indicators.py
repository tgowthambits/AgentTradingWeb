from loguru import logger
from Data.fyers_data_final import FyersDataScanner
# from utils.markov_util import count_pattern, count_total_pattern
import arrow
import pandas as pd
import numpy as np
from datetime import time
import ta
import plotly.graph_objects as go
import time

a = FyersDataScanner()
from_date = '2025-08-25 16:15:00'
to_date = '2025-08-27 16:30:00'
symbol= 'BSE:SENSEX2590480800PE'
# symbol = 'NSE:NIFTY25JUN25050PE'
# symbol = 'NSE:HDFCBANK-EQ'
# symbol = 'BSE:SENSEX-INDEX'
# symbol='BSE:SENSEX25MAY81700CE'
resolution  = '5S'
a.start_date = from_date
a.end_date = to_date
# a.symbol = 'NSE:NIFTYBANK-INDEX'
# a.symbol  = 'NSE:BANKNIFTY24O0152800PE'
a.symbol = symbol
a.resolution = resolution
# import pandas_ta as ta

trades = []
initial_capital = 20000  # Starting capital amount
equity = [initial_capital]  # Equity curve tracking
risk_per_trade = 0.03  # Risk 2% of capital per trade
stop_loss_pct = 0.002 # Stop-loss at 1% of entry price
profit_times =30
allowed_quantity = 2500

# best combo of expiry and strike of sensex
# stop_loss_pct = 0.0005 # Stop-loss at 1% of entry price
# profit_times =15
# allowed_quantity = 2500

def data():
    try:
        df = a.get_data()
        logger.info(f"Successfully loaded {len(df)} rows of market data")
        df = df.rename(columns={"TradeVol":"Volume"})
        logger.info("\nData sample:")
        logger.info(f"\n{df.head().to_string()}")
        logger.info(f"\nData columns: {df.columns.tolist()}")
        return df    
    except Exception as e:
        logger.exception("Error loading market data:")
        logger.warning("Using sample data for testing instead...")
        return None
        

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import ta

def calculate_trend_classifier(df, length=10):
    # Calculate SMEMA (SMA of EMA)
    df['ema'] = ta.trend.ema_indicator(df['Close'], window=length)
    df['smema'] = ta.trend.sma_indicator(df['ema'], window=length)
    
    # Calculate step based on high-low range
    df['step'] = ta.trend.ema_indicator(df['High'] - df['Low'], window=100)
    
    # Calculate SMEMA bands
    df['smema_up3'] = df['smema'] + df['step'] * 3
    df['smema_up2'] = df['smema'] + df['step'] * 2
    df['smema_up1'] = df['smema'] + df['step']
    df['smema_dn1'] = df['smema'] - df['step']
    df['smema_dn2'] = df['smema'] - df['step'] * 2
    df['smema_dn3'] = df['smema'] - df['step'] * 3
    
    # Determine trend
    df['trend'] = df['smema'] > df['smema'].shift(1)   
    
    # Check price position relative to bands
    df['above3'] = df['Close'] > df['smema_up3']
    df['above2'] = df['Close'] > df['smema_up2']
    df['above1'] = df['Close'] > df['smema_up1']
    df['below1'] = df['Close'] < df['smema_dn1']
    df['below2'] = df['Close'] < df['smema_dn2']
    df['below3'] = df['Close'] < df['smema_dn3']
    
    # Calculate strength
    df['bull_strength'] = df['above1'].astype(int) + df['above2'].astype(int) + df['above3'].astype(int)
    df['bear_strength'] = df['below1'].astype(int) + df['below2'].astype(int) + df['below3'].astype(int)
    
    # Determine signal
    conditions = [
        (df['trend'] & (df['bull_strength'] >= 1)),
        ((~df['trend']) & (df['bear_strength'] >= 1))
    ]
    choices = [1, -1]
    df['label_signal'] = np.select(conditions, choices, default=0)
    
    # Color classification
    df['color_class'] = np.where(df['label_signal'] > 0, '#008fa5', 
                            np.where(df['label_signal'] < 0, '#e14c60', '#edae49'))
    
    return df

# df = data()
# df = calculate_trend_classifier(df)
# df = df.sort_values(by='datetime')
# print(df)