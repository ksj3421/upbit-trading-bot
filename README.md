# Upbit Trading Bot

업비트 API를 활용한 암호화폐 자동매매 봇입니다. 모멘텀 전략과 평균회귀 전략을 지원합니다.

## 주요 기능

- 실시간 시장 분석 및 자동매매
- 백테스팅 기능 지원
- 다양한 기술적 지표 활용
  - RSI (상대강도지수)
  - MACD (이동평균수렴확산)
  - 볼린저 밴드
  - 스토캐스틱
  - 거래량 분석
- 손절/익절 자동화
- 상세한 거래 로깅
- 성과 분석 리포트

## 설치 방법

1. 리포지토리 클론:
```bash
git clone https://github.com/ksj3421/upbit-trading-bot.git
cd upbit-trading-bot
```

2. 가상환경 생성 및 활성화:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

3. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

4. 업비트 API 키 설정:
- `config.py` 파일에 업비트 API 키를 설정하세요.
```python
UPBIT_ACCESS_KEY = "your-access-key"
UPBIT_SECRET_KEY = "your-secret-key"
```

## 사용 방법

1. 백테스트 모드 실행:
```bash
python main.py
# 실행 모드 선택에서 1번 선택
```

2. 실시간 거래 모드 실행:
```bash
python main.py
# 실행 모드 선택에서 2번 선택
```

## 전략 설명

### 모멘텀 전략
- RSI, MACD, 스토캐스틱 등을 활용한 추세 추종 전략
- 상승/하락 추세를 포착하여 매매 시그널 생성
- 손절과 익절을 통한 리스크 관리

### 평균회귀 전략
- 볼린저 밴드를 활용한 평균회귀 전략
- 과매수/과매도 구간에서 반대 포지션 진입
- 거래량 확인을 통한 신뢰도 향상

## 주의사항

- 이 프로그램은 투자 손실을 초래할 수 있습니다.
- 실제 거래 전에 반드시 백테스트를 충분히 수행하세요.
- API 키는 절대로 공개되지 않도록 주의하세요.
- 거래소의 API 사용량 제한을 준수하세요.

## License

MIT License