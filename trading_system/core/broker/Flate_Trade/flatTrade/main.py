import hashlib

import requests

from api_helper import NorenApiPy
import logging

logging.basicConfig(level=logging.DEBUG)


class FlatData:

    def __init__(self) -> None:
        self.APIKEY = '8ee6ee6a7e8e49e38266639d15bbbad3'
        self.secretKey = '2024.137102b0d10c4750bd9b85471b64c32cce958efce1038018'
        self.totp_key = 'JOQ7SBK3UNWDNVHICRTO7562J53RYS4Y'
        self.password = 'Fucku@24'
        self.userid = 'FT042478'
        self.code = '17bf79de2a264928.a9b0f0b897b87c4e5da7445cc3cb866a5ddadcfc2203dde40868473936480c5a'
        self.token = '797472cf99f0b5b21b615c5128d709593769a7063667cf26b2cd33c7f66632a6'
        self.api = NorenApiPy()

    def __sha256(self, text):
        text_bytes = text.encode('utf-8')
        sha256_hash = hashlib.sha256(text_bytes).hexdigest()
        return sha256_hash

    def get_token(self):
        u = 'https://authapi.flattrade.in/trade/apitoken'
        text = self.APIKEY + self.code + self.secretKey
        pay = {
            "api_key": self.APIKEY, "request_code": self.code, "api_secret": self.__sha256(text)
        }
        r = requests.post(u, json=pay)
        if r.json()['stat'] == 'ok':
            self.token = r.json()['token']
            return self.token
        else:
            raise ('Token is not available')

    def session(self):

        ret = self.api.set_session(userid=self.userid, password='', usertoken=self.token)

        return self

    def search(self, exchange='NFO', searchtext='46500 CE'):
        result = self.api.searchscrip(exchange=exchange, searchtext=searchtext)
        return result

    def start_socket(self):
        self.api.start_websocket()
        return self


a = FlatData()
print('test')