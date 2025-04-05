import logging
from typing import Optional

import pandas as pd

from .upbit_api import UpbitAPI


class MeanReversionStrategy:
    def __init__(
        self,
        api: UpbitAPI,
        market: str,
        interval: str,
        rsi_period: int = 14,
        rsi_buy_threshold: float = 30,
        rsi_sell_threshold: float = 70,
    ):
        """Initialize the strategy with given parameters.

        Args:
            api: The Upbit API instance
            market: The market to trade (e.g., 'KRW-BTC')
            interval: The candle interval ('minute1', 'minute3', 'minute5', 'minute10',
                    'minute15', 'minute30', 'minute60', 'minute240', 'day')
            rsi_period: The period for RSI calculation
            rsi_buy_threshold: The RSI threshold for buy signals
            rsi_sell_threshold: The RSI threshold for sell signals
        """
        self.api = api
        self.market = market
        self.interval = interval
        self.rsi_period = rsi_period
        self.rsi_buy_threshold = rsi_buy_threshold
        self.rsi_sell_threshold = rsi_sell_threshold
        self.position = None  # 현재 포지션 상태
        self.entry_price = 0  # 진입 가격
        self.stop_loss_pct = 0.012  # 1.2% 손절
        self.take_profit_pct = 0.025  # 2.5% 익절
        self.total_fee = 0  # 총 누적 수수료
        self.trade_count = 0  # 총 거래 횟수
        self.initial_balance = None  # 시작 시 잔고 (성과 측정용)
        self.logger = logging.getLogger(__name__)
        self.trades_file = f"trades_{market}.log"

    def calculate_indicators(self, df, period=15, k=2):
        """
        지표 계산 (볼린저 밴드 + RSI + MACD + 스토캐스틱 + 거래량)
        """
        # 볼린저 밴드
        df["MA"] = df["close"].rolling(window=period).mean()
        df["STD"] = df["close"].rolling(window=period).std()
        df["UpperBand"] = df["MA"] + (k * df["STD"])
        df["LowerBand"] = df["MA"] - (k * df["STD"])

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = df["close"].ewm(span=12, adjust=False).mean()
        exp2 = df["close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = exp1 - exp2
        df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_Hist"] = df["MACD"] - df["Signal"]

        # 스토캐스틱
        period_k = 14
        period_d = 3
        low_min = df["low"].rolling(window=period_k).min()
        high_max = df["high"].rolling(window=period_k).max()
        df["K"] = ((df["close"] - low_min) / (high_max - low_min)) * 100
        df["D"] = df["K"].rolling(window=period_d).mean()

        # 거래량 지표
        df["Volume_MA"] = df["volume"].rolling(window=20).mean()
        df["Volume_Ratio"] = df["volume"] / df["Volume_MA"]

        return df

    def analyze_market(self):
        """시장 분석 및 매매 시그널 생성"""
        try:
            # 계좌 잔고 확인
            balance = self.api.get_account_balance()
            current_krw = self._get_krw_balance(balance)
            current_coin = self._get_coin_balance(balance)

            # 초기 잔고 설정 (첫 실행 시)
            self._initialize_balance(current_krw, current_coin)

            # 현재가 조회
            current_price = self._get_current_price()

            # 캔들 데이터 분석
            df = self._get_candle_data()
            latest = df.iloc[-1]

            # 매매 시그널 생성
            if current_coin == 0:
                return self._check_buy_signal(current_price, latest)
            else:
                return self._check_sell_signal(current_price, latest)

        except Exception as e:
            if self.logger:
                self.logger.error(f"시장 분석 중 오류 발생: {str(e)}")
            return None, None

    def _get_krw_balance(self, balance):
        """KRW 잔고 조회"""
        return float(
            next(
                (item["balance"] for item in balance if item["currency"] == "KRW"),
                0,
            )
        )

    def _get_coin_balance(self, balance):
        """코인 잔고 조회"""
        return float(
            next(
                (
                    item["balance"]
                    for item in balance
                    if item["currency"] == self.market.split("-")[1]
                ),
                0,
            )
        )

    def _initialize_balance(self, current_krw, current_coin):
        """초기 잔고 설정"""
        if self.initial_balance is None:
            current_price = float(
                self.api.get_current_price(self.market)[0]["trade_price"]
            )
            self.initial_balance = current_krw + (current_coin * current_price)
            if self.logger:
                self.logger.info(f"초기 자본: {self.initial_balance:,.0f}원")

    def _get_current_price(self):
        """현재가 조회"""
        current_price_info = self.api.get_current_price(self.market)[0]
        return float(current_price_info["trade_price"])

    def _get_candle_data(self):
        """캔들 데이터 조회 및 전처리"""
        interval_unit = int(self.interval.replace("minute", ""))
        candles = self.api.get_minute_candle(self.market, unit=interval_unit)

        # 데이터프레임 변환 및 전처리
        df = pd.DataFrame(candles)
        df = df.rename(
            columns={
                "opening_price": "open",
                "high_price": "high",
                "low_price": "low",
                "trade_price": "close",
                "candle_acc_trade_volume": "volume",
            }
        )

        # 시간 오름차순 정렬
        df = df.sort_values("candle_date_time_utc")

        # 지표 계산
        return self.calculate_indicators(df)

    def _check_buy_signal(self, current_price, latest):
        """매수 시그널 체크"""
        if (
            current_price < latest["LowerBand"]
            and latest["RSI"] < 30
            and (latest["MACD_Hist"] > 0 or latest["K"] < 20)
            and latest["Volume_Ratio"] > 1.1
        ):
            self.entry_price = current_price
            return "buy", "OVERSOLD"
        return None, None

    def _check_sell_signal(self, current_price, latest):
        """매도 시그널 체크"""
        # 손절 조건
        if current_price <= self.entry_price * (1 - self.stop_loss_pct):
            return "sell", "STOP_LOSS"

        # 익절 조건
        if current_price >= self.entry_price * (1 + self.take_profit_pct):
            return "sell", "TAKE_PROFIT"

        # 기술적 매도 시그널
        if self._check_technical_sell_signal(latest):
            return "sell", "TECH_SIGNAL"

        return None, None

    def _check_technical_sell_signal(self, latest):
        """기술적 매도 시그널 체크"""
        rsi_macd_signal = latest["RSI"] > 75 and latest["MACD_Hist"] < 0
        stoch_volume_signal = latest["K"] > 80 and latest["Volume_Ratio"] < 0.8
        return rsi_macd_signal or stoch_volume_signal

    def execute_trade(self, signal: Optional[str] = None) -> None:
        if not signal:
            return

        try:
            if signal == "buy":
                self._execute_buy_order()
            elif signal == "sell":
                self._execute_sell_order()
        except Exception as e:
            logging.error(f"Trade execution failed: {e}")

    def _execute_buy_order(self) -> None:
        try:
            balance = self._get_krw_balance()
            current_price = self._get_current_price()
            volume = self._calculate_buy_volume(balance, current_price)

            self.api.place_buy_order(self.market, volume)
            logging.info(f"매수 주문 체결 - 가격: {current_price}, 수량: {volume}")
        except Exception as e:
            logging.error(f"Buy order failed: {e}")

    def _execute_sell_order(self) -> None:
        try:
            coin_balance = self._get_coin_balance()
            current_price = self._get_current_price()

            self.api.place_sell_order(self.market, coin_balance)
            logging.info(
                f"매도 주문 체결 - 가격: {current_price}, 수량: {coin_balance}"
            )
        except Exception as e:
            logging.error(f"Sell order failed: {e}")

    def _calculate_buy_volume(self, available_krw, current_price):
        """매수 수량 계산"""
        # 최소 주문 금액 고려
        order_amount = min(available_krw, self.max_order_amount or available_krw)

        # 수수료를 고려한 실제 주문 가능 금액 계산
        actual_amount = order_amount / (1 + self.fee)

        # 주문 수량 계산 (소수점 8자리까지)
        return round(actual_amount / current_price, 8)


class MomentumStrategy(MeanReversionStrategy):
    """모멘텀 전략 (평균회귀 전략을 상속받아 일부 로직만 수정)"""

    def __init__(
        self, ticker="KRW-BTC", interval="minute15", logger=None, trades_file=None
    ):
        super().__init__(ticker, interval, logger, trades_file)
        self.stop_loss_pct = 0.015  # 1.5% 손절
        self.partial_profit_pct = 0.03  # 3% 1차 익절
        self.final_profit_pct = 0.05  # 5% 2차 익절
        self.position_size = 1.0  # 현재 포지션 크기 (1.0 = 100%)

    def analyze_market(self):
        """모멘텀 전략의 시장 분석 로직"""
        try:
            # 기본 시장 데이터 수집
            market_data = self._collect_market_data()
            if not market_data:
                return None, None

            current_price = market_data["current_price"]
            current_coin = market_data["current_coin"]
            latest = market_data["latest"]

            # 매매 신호 분석
            if current_coin == 0:
                return self._analyze_buy_signal(current_price, latest)
            else:
                return self._analyze_sell_signal(current_price, latest)

        except Exception as e:
            if self.logger:
                self.logger.error(f"시장 분석 중 오류 발생: {str(e)}")
            return None, None

    def _collect_market_data(self):
        """시장 데이터 수집 및 전처리"""
        try:
            # 계좌 잔고 확인
            balance = self.api.get_account_balance()
            current_krw, current_coin = self._get_balance_info(balance)

            # 초기 잔고 설정
            self._initialize_balance(current_krw, current_coin)

            # 현재가 및 캔들 데이터 조회
            current_price = self._get_current_price()
            df = self._get_processed_candle_data()

            return {
                "current_krw": current_krw,
                "current_coin": current_coin,
                "current_price": current_price,
                "latest": df.iloc[-1],
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"데이터 수집 중 오류 발생: {str(e)}")
            return None

    def _get_balance_info(self, balance):
        """잔고 정보 파싱"""
        current_krw = float(
            next((item["balance"] for item in balance if item["currency"] == "KRW"), 0)
        )
        current_coin = float(
            next(
                (
                    item["balance"]
                    for item in balance
                    if item["currency"] == self.market.split("-")[1]
                ),
                0,
            )
        )
        return current_krw, current_coin

    def _get_processed_candle_data(self):
        """캔들 데이터 조회 및 전처리"""
        interval_unit = int(self.interval.replace("minute", ""))
        candles = self.api.get_minute_candle(self.market, unit=interval_unit)

        df = pd.DataFrame(candles)
        df = df.rename(
            columns={
                "opening_price": "open",
                "high_price": "high",
                "low_price": "low",
                "trade_price": "close",
                "candle_acc_trade_volume": "volume",
            }
        )
        df = df.sort_values("candle_date_time_utc")
        return self.calculate_indicators(df)

    def _analyze_buy_signal(self, current_price, latest):
        """매수 신호 분석"""
        if (
            latest["RSI"] > 50
            and latest["MACD_Hist"] > 0
            and current_price > latest["MA"]
            and latest["Volume_Ratio"] > 1.2
        ):
            self.entry_price = current_price
            return "buy", "MOMENTUM_ENTRY"
        return None, None

    def _analyze_sell_signal(self, current_price, latest):
        """매도 신호 분석"""
        # 손절 조건
        if current_price <= self.entry_price * (1 - self.stop_loss_pct):
            self.position_size = 1.0  # 포지션 크기 초기화
            return "sell", "STOP_LOSS"

        # 1차 익절 조건
        if self._check_partial_profit(current_price):
            self.position_size = 0.5  # 50% 매도
            return "sell", "PARTIAL_PROFIT"

        # 2차 익절 조건
        if self._check_final_profit(current_price):
            self.position_size = 0.0  # 완전 매도
            return "sell", "FINAL_PROFIT"

        # 추세 반전 조건
        if self._check_trend_reversal(current_price, latest):
            self.position_size = 0.0  # 완전 매도
            return "sell", "TREND_REVERSAL"

        return None, None

    def _check_partial_profit(self, current_price):
        """1차 익절 조건 확인"""
        return (
            current_price >= self.entry_price * (1 + self.partial_profit_pct)
            and self.position_size == 1.0
        )

    def _check_final_profit(self, current_price):
        """2차 익절 조건 확인"""
        return (
            current_price >= self.entry_price * (1 + self.final_profit_pct)
            and self.position_size == 0.5
        )

    def _check_trend_reversal(self, current_price, latest):
        """추세 반전 조건 확인"""
        return (
            latest["RSI"] < 40
            and latest["MACD_Hist"] < 0
            and current_price < latest["MA"]
        )
