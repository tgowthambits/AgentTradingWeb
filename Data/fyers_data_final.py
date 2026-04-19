import json
from loguru import logger
import numpy as np
import pandas as pd
import arrow
from .DATA_SOURCE import FyersData



class FyersDataScanner:
    def __init__(self) -> None:
        self.symbol = 'NSE:BANKNIFTY24O0155000PE'
        self.start_date = '2024-09-26 16:15:00'
        self.end_date = '2024-09-27 16:30:00'
        self.resolution = '1'
        self.return_up = 10
        self.return_down = 0
        self.data = FyersData()

    def get_data(self):          
        logger.info(f'Getting data for {self.symbol} from {self.start_date} to {self.end_date} ')
        logger.info(f'Resolution: {self.resolution}')
        self.data.resolution = self.resolution
        # self.data.symbol = 'NSE:NIFTYBANK-INDEX'
        self.data.symbol = self.symbol
        self.data.start_date =  arrow.get(self.start_date).int_timestamp
        self.data.end_date = arrow.get(self.end_date).int_timestamp
        self.df = self.data.get_data()
        # self.df['daily_return'] = self.df['Close'].pct_change()
        self.df['daily_return_open_close'] = self.df['Close'] - self.df['Close'].shift(1)
        self.df['daily_return'] = self.df['Close'] - self.df['Open']
        self.df['state'] = np.where(self.df['daily_return'] >= 0, "up", "down")
        self.df['state'] = np.where(self.df['daily_return'] > self.return_up, "up", 
                            np.where(self.df['daily_return'] < self.return_down, "down", 
                                     "no"))
        logger.info(f'Data: {self.df.shape[0]} rows') 
        self.df.sort_values(by='datetime', inplace=True) 
      
        return self.df 
     

   
    def next_pred(self,df):
        try:

            last_3 = df['state'].values

            joined_string_up = '_'.join(last_3) + '_up' + '_probabily'
            joined_string_down = '_'.join(last_3) + '_down' + '_probabily'

            if joined_string_up in df.columns and joined_string_down in df.columns:
                prob = df[[joined_string_up, joined_string_down]].iloc[-1]
                # print(prob[[joined_string_up, joined_string_down]])
                
                if prob[joined_string_up] >= 0 and prob[joined_string_down] >= 0:
                    prediction = 'up' if prob[joined_string_down] < prob[joined_string_up] else 'down'
                    
                else:
                    prediction = 'stop'
                return prediction,  json.loads(json.dumps(prob.to_dict()))
            else:
                logger.info(f'pattern not found - {joined_string_up} {joined_string_down}')
                return 'NP' , {'NP': 'NP'}
        except Exception as e:
            logger.error(e)
            return 'ER',    {'ER': 'ER'}

# a = FyersDataScanner()
# a.get_data()