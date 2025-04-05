import hashlib
import uuid
from urllib.parse import urlencode

import jwt
import requests


class UpbitAPI:
    """Upbit API wrapper class"""

    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = "https://api.upbit.com/v1"

    def _get_headers(self, query=None):
        """JWT 토큰이 포함된 헤더 생성"""
        payload = {"access_key": self.access_key, "nonce": str(uuid.uuid4())}

        if query:
            m = hashlib.sha512()
            m.update(query.encode())
            query_hash = m.hexdigest()
            payload["query_hash"] = query_hash
            payload["query_hash_alg"] = "SHA512"

        jwt_token = jwt.encode(payload, self.secret_key)
        return {"Authorization": f"Bearer {jwt_token}"}

    def get_current_price(self, ticker):
        """현재가 조회"""
        url = f"{self.base_url}/ticker"
        params = {"markets": ticker}
        response = requests.get(url, params=params)
        return response.json()

    def get_minute_candle(self, ticker, unit=1, count=200):
        """분봉 데이터 조회"""
        url = f"{self.base_url}/candles/minutes/{unit}"
        params = {"market": ticker, "count": count}
        response = requests.get(url, params=params)
        return response.json()

    def get_account_balance(self):
        """계좌 잔고 조회"""
        url = f"{self.base_url}/accounts"
        headers = self._get_headers()
        response = requests.get(url, headers=headers)
        return response.json()

    def place_order(self, ticker, side, volume, price=None, ord_type="limit"):
        """주문 실행"""
        url = f"{self.base_url}/orders"
        data = {
            "market": ticker,
            "side": side,  # bid(매수) / ask(매도)
            "ord_type": ord_type,
        }

        if ord_type == "limit":  # 지정가 주문
            data["price"] = price
            data["volume"] = volume
        else:  # 시장가 주문
            if side == "bid":
                data["price"] = price  # 매수금액
            else:
                data["volume"] = volume  # 매도수량

        query = urlencode(data)
        headers = self._get_headers(query)

        response = requests.post(url, json=data, headers=headers)
        return response.json()

    def get_order_status(self, uuid_str):
        """주문 상태 조회"""
        url = f"{self.base_url}/order"
        data = {"uuid": uuid_str}
        query = urlencode(data)
        headers = self._get_headers(query)

        response = requests.get(url, params=data, headers=headers)
        return response.json()

    def cancel_order(self, uuid_str):
        """주문 취소"""
        url = f"{self.base_url}/order"
        data = {"uuid": uuid_str}
        query = urlencode(data)
        headers = self._get_headers(query)

        response = requests.delete(url, params=data, headers=headers)
        return response.json()

    def get_order_book(self, ticker):
        """호가 정보 조회"""
        url = f"{self.base_url}/orderbook"
        params = {"markets": ticker}
        response = requests.get(url, params=params)
        return response.json()

    def get_daily_candle(self, ticker, count=200):
        """일봉 데이터 조회"""
        url = f"{self.base_url}/candles/days"
        params = {"market": ticker, "count": count}
        response = requests.get(url, params=params)
        return response.json()
