from fastapi import FastAPI
from pydantic import BaseModel
from pipeline.live_inference import live_inference
from backtester.engine import BacktestEngine
from backtester.metrics import Metrics
import pandas as pd
import uvicorn


app = FastAPI(title="Hybrid Trading AI Server", version="1.0")


# ---------- REQUEST SCHEMAS ----------
class InferenceRequest(BaseModel):
    daily_data: list
    intraday_data: list
    intraday_prices: list


class BacktestRequest(BaseModel):
    prices: list
    signals: list


# ---------- ROUTES ----------
@app.get("/health")
def health():
    return {"status": "OK", "message": "Trading server alive"}


@app.post("/signal")
def generate_signal(req: InferenceRequest):
    daily_df = pd.DataFrame(req.daily_data)
    intraday_df = pd.DataFrame(req.intraday_data)

    output = live_inference(
        daily_df,
        intraday_df,
        req.intraday_prices
    )
    return output


@app.post("/backtest")
def run_backtest(req: BacktestRequest):
    engine = BacktestEngine(
        prices=req.prices,
        signals=req.signals
    )
    results = engine.run()
    metrics = Metrics.compute(pd.DataFrame(results))
    return {"metrics": metrics, "results": results}


@app.get("/")
def root():
    return {"service": "Hybrid AI Trading Server", "status": "running"}


if __name__ == "__main__":
    uvicorn.run("trading_api:app", host="0.0.0.0", port=8000)
