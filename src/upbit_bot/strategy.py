from .upbit_api import UpbitAPI
import pandas as pd
import numpy as np
import time
from datetime import datetime

class MeanReversionStrategy:
    def __init__(self, ticker="KRW-BTC", interval="minute15", logger=None, trades_file=None):
        """
        Mean Reversion 전략
        :param ticker: 코인 티커 (예: KRW-BTC)
        :param interval: 봉 간격 (minute1, minute3, minute5, minute10, minute15, minute30, minute60, day, week, month)
        :param logger: 로깅을 위한 logger 객체
        :param trades_file: 거래 기록을 저장할 CSV 파일 경로
        """
        self.api = UpbitAPI()
        self.ticker = ticker
        self.interval = interval
        self.position = None  # 현재 포지션 상태
        self.entry_price = 0  # 진입 가격
        self.stop_loss_pct = 0.012  # 1.2% 손절
        self.take_profit_pct = 0.025  # 2.5% 익절
        self.total_fee = 0  # 총 누적 수수료
        self.trade_count = 0  # 총 거래 횟수
        self.initial_balance = None  # 시작 시 잔고 (성과 측정용)
        self.logger = logger  # 로거
        self.trades_file = trades_file  # 거래 기록 파일
        
    def calculate_indicators(self, df, period=15, k=2):
        """
        지표 계산 (볼린저 밴드 + RSI + MACD + 스토캐스틱 + 거래량)
        """
        # 볼린저 밴드
        df['MA'] = df['close'].rolling(window=period).mean()
        df['STD'] = df['close'].rolling(window=period).std()
        df['UpperBand'] = df['MA'] + (k * df['STD'])
        df['LowerBand'] = df['MA'] - (k * df['STD'])
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal']
        
        # 스토캐스틱
        period_k = 14
        period_d = 3
        low_min = df['low'].rolling(window=period_k).min()
        high_max = df['high'].rolling(window=period_k).max()
        df['K'] = ((df['close'] - low_min) / (high_max - low_min)) * 100
        df['D'] = df['K'].rolling(window=period_d).mean()
        
        # 거래량 지표
        df['Volume_MA'] = df['volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['volume'] / df['Volume_MA']
        
        return df

    def analyze_market(self):
        """시장 분석 및 매매 시그널 생성"""
        try:
            # 계좌 잔고 확인
            balance = self.api.get_account_balance()
            current_krw = float(next((item['balance'] for item in balance if item['currency'] == 'KRW'), 0))
            current_coin = float(next((item['balance'] for item in balance if item['currency'] == self.ticker.split('-')[1]), 0))
            
            # 초기 잔고 설정 (첫 실행 시)
            if self.initial_balance is None:
                self.initial_balance = current_krw + (current_coin * float(self.api.get_current_price(self.ticker)[0]['trade_price']))
                if self.logger:
                    self.logger.info(f"초기 자본: {self.initial_balance:,.0f}원")
            
            # 현재가 조회
            current_price_info = self.api.get_current_price(self.ticker)[0]
            current_price = float(current_price_info['trade_price'])
            
            # 최근 캔들 데이터 조회
            interval_unit = int(self.interval.replace('minute', ''))
            candles = self.api.get_minute_candle(self.ticker, unit=interval_unit)
            
            # 데이터프레임 변환 및 전처리
            df = pd.DataFrame(candles)
            df = df.rename(columns={
                'opening_price': 'open',
                'high_price': 'high',
                'low_price': 'low',
                'trade_price': 'close',
                'candle_acc_trade_volume': 'volume'
            })
            
            # 시간 오름차순 정렬
            df = df.sort_values('candle_date_time_utc')
            
            # 지표 계산
            df = self.calculate_indicators(df)
            
            # 가장 최근 데이터
            latest = df.iloc[-1]
            
            # 매매 시그널 생성
            signal = None
            reason = None
            
            # 1. 포지션이 없을 때 (매수 기회 탐색)
            if current_coin == 0:
                # 매수 조건:
                # 1) RSI 30 이하 (과매도)
                # 2) 볼린저 밴드 하단 아래
                # 3) MACD 히스토그램이 상승 반전 또는 스토캐스틱 < 20
                # 4) 거래량이 평균보다 많음
                if (current_price < latest['LowerBand'] and 
                    latest['RSI'] < 30 and
                    (latest['MACD_Hist'] > 0 or latest['K'] < 20) and
                    latest['Volume_Ratio'] > 1.1):
                    signal = 'buy'
                    reason = 'OVERSOLD'
                    self.entry_price = current_price
            
            # 2. 포지션 보유 중 (매도 기회 탐색)
            else:
                # 손절 조건
                if current_price <= self.entry_price * (1 - self.stop_loss_pct):
                    signal = 'sell'
                    reason = 'STOP_LOSS'
                # 익절 조건
                elif current_price >= self.entry_price * (1 + self.take_profit_pct):
                    signal = 'sell'
                    reason = 'TAKE_PROFIT'
                # 기술적 매도 시그널
                elif ((latest['RSI'] > 75 and latest['MACD_Hist'] < 0) or  # RSI 과매수 + MACD 하락
                      (latest['K'] > 80 and latest['Volume_Ratio'] < 0.8)):  # 스토캐스틱 과매수 + 거래량 감소
                    signal = 'sell'
                    reason = 'TECH_SIGNAL'
            
            return signal, reason
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"시장 분석 중 오류 발생: {str(e)}")
            return None, None

    def execute_trade(self, signal, reason=None):
        """매매 시그널에 따른 거래 실행"""
        try:
            # 계좌 잔고 확인
            balance = self.api.get_account_balance()
            krw_balance = float(next((item['balance'] for item in balance if item['currency'] == 'KRW'), 0))
            coin_balance = float(next((item['balance'] for item in balance if item['currency'] == self.ticker.split('-')[1]), 0))
            
            current_price = float(self.api.get_current_price(self.ticker)[0]['trade_price'])
            
            if signal == 'buy' and krw_balance >= 5000:  # 최소 주문 금액 5000원
                # 매수 가능 금액 계산 (수수료 고려)
                available_krw = krw_balance * 0.9995  # 수수료 0.05% 고려
                
                # 주문 실행
                order = self.api.place_order(
                    ticker=self.ticker,
                    side='bid',
                    price=available_krw,
                    ord_type='price'  # 시장가 매수
                )
                
                if order.get('uuid'):
                    self.trade_count += 1
                    self.total_fee += available_krw * 0.0005  # 수수료 기록
                    
                    if self.logger:
                        self.logger.info(f"매수 주��� 체결 - 금액: {available_krw:,.0f}원, 이유: {reason}")
                    
                    # 거래 기록
                    if self.trades_file:
                        with open(self.trades_file, 'a') as f:
                            f.write(f"{datetime.now()},buy,{current_price},{available_krw/current_price},{krw_balance},{self.total_fee},{reason}\n")
                
            elif signal == 'sell' and coin_balance > 0:
                # 주문 실행
                order = self.api.place_order(
                    ticker=self.ticker,
                    side='ask',
                    volume=coin_balance,
                    ord_type='market'  # 시장가 매도
                )
                
                if order.get('uuid'):
                    self.trade_count += 1
                    sell_amount = coin_balance * current_price
                    self.total_fee += sell_amount * 0.0005  # 수수료 기록
                    
                    if self.logger:
                        self.logger.info(f"매도 주문 체결 - 수량: {coin_balance} {self.ticker}, 이유: {reason}")
                    
                    # 거래 기록
                    if self.trades_file:
                        with open(self.trades_file, 'a') as f:
                            f.write(f"{datetime.now()},sell,{current_price},{coin_balance},{krw_balance},{self.total_fee},{reason}\n")
                            
        except Exception as e:
            if self.logger:
                self.logger.error(f"주문 실행 중 오류 발생: {str(e)}")

class MomentumStrategy(MeanReversionStrategy):
    """모멘텀 전략 (평균회귀 전략을 상속받아 일부 로직만 수정)"""
    
    def __init__(self, ticker="KRW-BTC", interval="minute15", logger=None, trades_file=None):
        super().__init__(ticker, interval, logger, trades_file)
        self.stop_loss_pct = 0.015  # 1.5% 손절
        self.partial_profit_pct = 0.03  # 3% 1차 익절
        self.final_profit_pct = 0.05  # 5% 2차 익절
        self.position_size = 1.0  # 현재 포지션 크기 (1.0 = 100%)

    def analyze_market(self):
        """모멘텀 전략의 시장 분석 로직"""
        try:
            # 계좌 잔고 확인
            balance = self.api.get_account_balance()
            current_krw = float(next((item['balance'] for item in balance if item['currency'] == 'KRW'), 0))
            current_coin = float(next((item['balance'] for item in balance if item['currency'] == self.ticker.split('-')[1]), 0))
            
            # 초기 잔고 설정 (첫 실행 시)
            if self.initial_balance is None:
                self.initial_balance = current_krw + (current_coin * float(self.api.get_current_price(self.ticker)[0]['trade_price']))
                if self.logger:
                    self.logger.info(f"초기 자본: {self.initial_balance:,.0f}원")
            
            # 현재가 조회
            current_price_info = self.api.get_current_price(self.ticker)[0]
            current_price = float(current_price_info['trade_price'])
            
            # 최근 캔들 데이터 조회
            interval_unit = int(self.interval.replace('minute', ''))
            candles = self.api.get_minute_candle(self.ticker, unit=interval_unit)
            
            # 데이터프레임 변환
            df = pd.DataFrame(candles)
            df = df.rename(columns={
                'opening_price': 'open',
                'high_price': 'high',
                'low_price': 'low',
                'trade_price': 'close',
                'candle_acc_trade_volume': 'volume'
            })
            
            # 시간 오름차순 정렬
            df = df.sort_values('candle_date_time_utc')
            
            # 지표 계산
            df = self.calculate_indicators(df)
            
            # 가장 최근 데이터
            latest = df.iloc[-1]
            
            signal = None
            reason = None
            
            # 1. 포지션이 없을 때 (매수 기회 탐색)
            if current_coin == 0:
                # 매수 조건:
                # 1) RSI > 50 (상승 추세)
                # 2) MACD 히스토그램 양수 (상승 모멘텀)
                # 3) 20일 이동평균선 위에서 거래
                # 4) 거래량 증가
                if (latest['RSI'] > 50 and
                    latest['MACD_Hist'] > 0 and
                    current_price > latest['MA'] and
                    latest['Volume_Ratio'] > 1.2):
                    signal = 'buy'
                    reason = 'MOMENTUM_ENTRY'
                    self.entry_price = current_price
            
            # 2. 포지션 보유 중 (매도 기회 탐색)
            else:
                # 손절 조건
                if current_price <= self.entry_price * (1 - self.stop_loss_pct):
                    signal = 'sell'
                    reason = 'STOP_LOSS'
                    self.position_size = 1.0  # 포지션 크기 초기화
                
                # 1차 익절 (50% 물량)
                elif (current_price >= self.entry_price * (1 + self.partial_profit_pct) and
                      self.position_size == 1.0):
                    signal = 'sell'
                    reason = 'PARTIAL_PROFIT'
                    self.position_size = 0.5  # 50% 매도
                
                # 2차 익절 (나머지 물량)
                elif (current_price >= self.entry_price * (1 + self.final_profit_pct) and
                      self.position_size == 0.5):
                    signal = 'sell'
                    reason = 'FINAL_PROFIT'
                    self.position_size = 0.0  # 완전 매도
                
                # 추세 반전 매도
                elif (latest['RSI'] < 40 and
                      latest['MACD_Hist'] < 0 and
                      current_price < latest['MA']):
                    signal = 'sell'
                    reason = 'TREND_REVERSAL'
                    self.position_size = 0.0  # 완전 매도
            
            return signal, reason
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"시장 분석 중 오류 발생: {str(e)}")
            return None, None