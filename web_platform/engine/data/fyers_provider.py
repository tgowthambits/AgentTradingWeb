"""
Optional Fyers API data provider.

Fetches OHLCV data from the Fyers API and returns a pandas DataFrame.
Falls back gracefully if dependencies (arrow, requests, omegaconf) are missing.
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger("engine.data.fyers")

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "fyers_config.yaml"

try:
    import arrow
    import requests
    from omegaconf import OmegaConf
    FYERS_AVAILABLE = True
except ImportError:
    FYERS_AVAILABLE = False


def is_available() -> bool:
    if not FYERS_AVAILABLE:
        return False
    if not _CONFIG_PATH.exists():
        return False
    return True


class FyersDataFetcher:
    """Fetches historical candle data from the Fyers API."""

    def __init__(self, config_path: str = None):
        if not FYERS_AVAILABLE:
            raise ImportError("Fyers provider requires: arrow, requests, omegaconf")

        cfg_path = Path(config_path) if config_path else _CONFIG_PATH
        if not cfg_path.exists():
            raise FileNotFoundError(f"Fyers config not found: {cfg_path}")

        cfg = OmegaConf.load(cfg_path)
        self.headers = {
            "Accept": "*/*",
            "Authorization": cfg.Fyers.Authorization,
            "User-Agent": "Mozilla/5.0",
        }
        self.token_id = cfg.Fyers.token_id
        self.api_url = cfg.Fyers.api_url

    def fetch(self, symbol: str, start_date: str, end_date: str,
              resolution: str = "1") -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol.

        Args:
            symbol: e.g. "NSE:NIFTY2642124250PE"
            start_date: e.g. "2026-04-15 09:15"
            end_date: e.g. "2026-04-15 15:30"
            resolution: candle resolution string

        Returns:
            DataFrame with columns: Time, Open, High, Low, Close, TradeVol, date, datetime
        """
        start_ts = arrow.get(start_date).int_timestamp
        end_ts = arrow.get(end_date).int_timestamp

        payload = {
            "symbol": symbol,
            "resolution": resolution,
            "from": start_ts,
            "to": end_ts,
            "token_id": self.token_id,
            "dataReq": arrow.now().int_timestamp,
            "contFlag": 1,
            "countback": 12,
            "currencyCode": "INR",
        }

        resp = requests.get(self.api_url, params=payload, headers=self.headers,
                            verify=False, timeout=30)
        resp_json = resp.json()

        if "code" in resp_json and resp_json["code"] != 200:
            raise ValueError(f"Fyers API error: {resp_json.get('message', resp.text[:200])}")

        if "candles" not in resp_json:
            raise ValueError(f"No candle data in response for {symbol}")

        data = resp_json["candles"]
        try:
            df = pd.DataFrame(data, columns=["Time", "Open", "High", "Low", "Close", "TradeVol"])
        except Exception:
            df = pd.DataFrame(data, columns=["Time", "Open", "High", "Low", "Close", "TradeVol", "Vol"])

        def ts_to_arrow(ts):
            return arrow.get(ts).to("Asia/Kolkata")

        df["date"] = df["Time"].apply(ts_to_arrow)
        df["datetime"] = df["Time"].apply(lambda x: ts_to_arrow(x).format("MM-DD-YYYY HH:mm:ss"))

        logger.info("Fetched %d candles for %s", len(df), symbol)
        return df
