import pandas as pd
import arrow
from loguru import logger
import requests
from omegaconf import OmegaConf
from pathlib import Path

# Get the directory of this file and construct path to config.yaml
_config_path = Path(__file__).parent / "config" / "config.yaml"
config = OmegaConf.load(_config_path)



class FyersData:

    def __init__(self):
        # print("FyersData",Session.objects.last().session_id, Session.objects.last().token)
        self.headers = {
            'Accept': '*/*',
            'Authorization': config.Fyers.Authorization,

            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
        }
        self.token_id = config.Fyers.token_id
        # self.symbol = 'NSE:NIFTYBANK-INDEX'
        self.symbol = 'NSE:BANKNIFTY24SEP55000CE'
        self.resolution = '1'
        self.start_date = arrow.get('2024-09-19 16:15:00').int_timestamp
        self.end_date = arrow.get('2024-09-20 16:30:00').int_timestamp
        self.payload = {
            'symbol': self.symbol,
            'resolution': self.resolution,
            'from': self.start_date,
            'to': self.end_date,
            'token_id': self.token_id,
            'dataReq': arrow.now().int_timestamp,
            'contFlag': 0,
            'countback': 10,
            'currencyCode': 'INR'
        }
        self.api_url = config.Fyers.api_url

    def seconds_to_date(self, seconds, format_date=False):
        """Converts seconds to a date string in the format 'dd-mm-yyyy'"""
        time = arrow.get(seconds).to('Asia/Kolkata')
        if format_date:
            return time.format("MM-DD-YYYY HH:mm:ss")
        # return time.format("DD-MM-YYYY HH:mm:ss")
        else:
            return time
    def __refresh_payload__(self):
        self.payload = {
            'symbol': self.symbol,
            'resolution': self.resolution,
            'from': self.start_date,
            'to': self.end_date,
            'token_id': self.token_id,
            'dataReq': arrow.now().int_timestamp,
            'contFlag': 1,
            'countback': 12,
            'currencyCode': 'INR'
        }
    def get_data(self):
        # import requests_cache
        cache_name = f'fyers_cache_{self.symbol}_{self.start_date}_{self.end_date}_{self.resolution}'
        logger.info(f"Cache name: {cache_name}")
        # with requests_cache.CachedSession(cache_name, backend='sqlite', expire_after=600*6000) as session:
        self.__refresh_payload__()
        response = requests.get(self.api_url, params=self.payload, headers=self.headers, verify=False)
        # logger.info(f"Response: {response.text}")
        
        # Parse JSON response safely
        try:
            response_json = response.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response.text}")
            raise ValueError(f"Invalid JSON response from Fyers API: {response.text[:200]}")
        
        # Check for error codes if present
        if 'code' in response_json and response_json['code'] != 200:
            logger.error(f"Fyers API returned error code: {response_json.get('code')}")
            logger.error(f"Response: {response.text}")
            raise ValueError(f"Fyers API error: {response_json.get('message', 'Unknown error')}")
        
        # Extract candles data
        if 'candles' not in response_json:
            logger.error(f"No 'candles' key in response: {response.text[:500]}")
            raise ValueError(f"Invalid response structure from Fyers API - missing 'candles' data")
        
        data = response_json['candles']
        try:
            df = pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'TradeVol'])
            # if logger.level("DEBUG"):
            # print(response.text)
            # print(self.start_date, self.end_date)
        except Exception as e:
            # print(response.text)
            # print(self.start_date, self.end_date)
            # print(f"Error in fetching data: {response.text}")
            logger.error(f"Error in fetching data: {e}")
            df = pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'TradeVol', 'Vol'])
        df['date'] = df['Time'].apply(lambda x: self.seconds_to_date(x))
        df['datetime'] = df['Time'].apply(lambda x: self.seconds_to_date(x, True))

        return df
    def search(self,script_name):
        # Define the URL
        url = "https://api-t1.fyers.in/indus/data/v1/search"

        # Define the query parameters
        params = {
            "limit": 30,
            "query": script_name,
            "type": "",
            "exchange": "",
            "dataReq": arrow.now().int_timestamp,
            "token_id": self.token_id
        }

        # Make the POST request
        response = requests.get(url, params=params, headers=self.headers)
        if response.status_code != 200:
            logger.exception(f"Error in fetching data: {response.text}")
        return response.json()

# a = FyersData()
# a.get_data()