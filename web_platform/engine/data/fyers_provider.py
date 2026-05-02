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
OPTIONS_CHAIN_URL = "https://api-t1.fyers.in/indus/data/v1/options-chain"

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

    def fetch_options_chain_raw(
        self,
        symbol: str,
        *,
        timestamp: str | None = None,
        strikecount: int | None = None,
    ) -> dict:
        """
        Call Fyers options-chain API (same auth as history).

        Args:
            symbol: Underlying, e.g. ``BSE:SENSEX-INDEX``.
            timestamp: Optional expiry epoch string (from ``expiryData[].expiry``).
            strikecount: Optional strike window size around ATM.

        Returns:
            Parsed JSON dict (includes ``code``, ``data``, ``message``).
        """
        params: dict = {"symbol": symbol}
        if timestamp:
            params["timestamp"] = str(timestamp)
        if strikecount is not None:
            params["strikecount"] = int(strikecount)

        resp = requests.get(
            OPTIONS_CHAIN_URL,
            params=params,
            headers=self.headers,
            verify=False,
            timeout=45,
        )
        try:
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("options-chain non-JSON: %s", resp.text[:300])
            raise ValueError(f"Invalid JSON from options-chain: {exc}") from exc


def normalize_options_chain(api_json: dict) -> dict:
    """
    Turn Fyers options-chain JSON into a compact structure for the web UI.

    Returns ``{ok, error?, underlying, indiavix, expiryData, strikes, spot, atm_strike}``.
    """
    if not api_json:
        return {"ok": False, "error": "empty response"}
    if api_json.get("code") != 200:
        return {
            "ok": False,
            "error": api_json.get("message") or str(api_json.get("code")),
        }

    data = api_json.get("data") or {}
    chain = data.get("optionsChain") or []
    underlying = None
    by_strike: dict[int, dict] = {}

    for row in chain:
        sp = row.get("strike_price")
        ot = (row.get("option_type") or "").strip()
        if sp is None or sp < 0 or not ot:
            underlying = row
            continue
        strike = int(sp)
        if strike not in by_strike:
            by_strike[strike] = {"strike": strike, "ce": None, "pe": None}
        side = "ce" if ot == "CE" else "pe"
        by_strike[strike][side] = {
            "symbol": row.get("symbol"),
            "ltp": row.get("ltp"),
            "ltpch": row.get("ltpch"),
            "ltpchp": row.get("ltpchp"),
            "oi": row.get("oi"),
            "volume": row.get("volume"),
            "bid": row.get("bid"),
            "ask": row.get("ask"),
        }

    spot = 0.0
    if underlying and underlying.get("ltp") is not None:
        try:
            spot = float(underlying["ltp"])
        except (TypeError, ValueError):
            spot = 0.0

    strikes_sorted = sorted(by_strike.keys())
    atm_strike = None
    if strikes_sorted and spot > 0:
        atm_strike = min(strikes_sorted, key=lambda s: abs(s - spot))

    rows = []
    for k in strikes_sorted:
        entry = by_strike[k]
        rows.append(
            {
                "strike": k,
                "atm": k == atm_strike,
                "ce": entry["ce"],
                "pe": entry["pe"],
            }
        )

    return {
        "ok": True,
        "underlying": underlying,
        "indiavix": data.get("indiavixData"),
        "expiryData": data.get("expiryData"),
        "callOi": data.get("callOi"),
        "putOi": data.get("putOi"),
        "strikes": rows,
        "spot": spot,
        "atm_strike": atm_strike,
    }


class FyersData(FyersDataFetcher):
    """Fyers market data: historical candles (``fetch``) and options chain (``fetch_options_chain_raw``)."""

    pass
