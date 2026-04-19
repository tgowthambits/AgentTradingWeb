import time
from pipeline.live_inference import live_inference
from Data.fyers_data_final import load_intraday, load_daily

def live_loop():
    print("Starting 5-second live loop...")

    while True:
        try:
            daily_df = load_daily()
            intraday_df, prices = load_intraday()

            output = live_inference(daily_df, intraday_df, prices)

            print(" Live Signal:", output["final_signal"])

            # TODO: call fyers.place_order() here
            # if output["final_signal"] == 1: BUY
            # if output["final_signal"] == -1: SELL

        except Exception as e:
            print("ERROR:", e)

        time.sleep(5)   # <-- 5-second interval

"""
from fyers_apiv3 import fyersModel

def place_order(signal, symbol, qty):

    if signal == 1:
        side = 1  # BUY
    elif signal == -1:
        side = -1 # SELL
    else:
        return

    order = {
        "symbol": symbol,
        "qty": qty,
        "type": 2,
        "side": side,
        "productType": "INTRADAY",
        "limitPrice": 0,
        "stopPrice": 0,
        "disclosedQty": 0,
        "validity": "DAY",
        "offlineOrder": "False",
        "stopLoss": 0,
        "takeProfit": 0
    }

    fyers.place_order(order)
"""
# signal = output["final_signal"]
# place_order(signal, "NSE:NIFTY25DEC18000CE", qty=50)