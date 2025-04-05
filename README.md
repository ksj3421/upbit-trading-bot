# Upbit Trading Bot

Upbit API를 활용한 자동화된 암호화폐 트레이딩 봇입니다. 모멘텀과 평균회귀 전략을 지원하며, 실시간 시장 분석과 자동 매매 기능을 제공합니다.

## 주요 기능

- 실시간 시장 분석
- 백테스팅 기능
- 다양한 기술적 지표 활용
  - RSI (상대강도지수)
  - MACD (이동평균수렴확산)
  - 볼린저 밴드
  - 스토캐스틱
  - 거래량 분석
- 자동 손절/익절
- 상세한 거래 로깅
- 성과 분석 리포트

## 설치 방법

### 사전 요구사항

- Python 3.9 이상
- [Poetry](https://python-poetry.org/docs/#installation)
- Upbit API 키

### 설치 단계

1. 저장소 클론
```bash
git clone https://github.com/ksj3421/upbit-trading-bot.git
cd upbit-trading-bot
```

2. Poetry를 사용하여 의존성 설치
```bash
poetry install
```

3. 환경 변수 설정
`.env` 파일을 생성하고 Upbit API 키를 설정:
```
UPBIT_ACCESS_KEY=your_access_key
UPBIT_SECRET_KEY=your_secret_key
```

## 사용 방법

1. Poetry 환경 활성화
```bash
poetry shell
```

2. 트레이딩 봇 실행
```bash
python -m src.upbit_bot.main
```

실행 시 다음 옵션을 선택할 수 있습니다:
- 전략 선택 (모멘텀/평균회귀)
- 거래 코인 선택
- 차트 인터벌 설정 (1분, 3분, 5분, 15분, 30분, 60분)

## 트레이딩 전략

### 모멘텀 전략
추세 추종 전략으로, 가격의 상승/하락 추세를 따라가며 거래합니다.
- MACD 시그널
- RSI 과매수/과매도
- 볼린저 밴드 브레이크아웃
- 거래량 확인

### 평균회귀 전략
반추세 전략으로, 가격이 평균으로 회귀하는 특성을 이용합니다.
- 볼린저 밴드 범위 거래
- RSI 다이버전스
- 스토캐스틱 크로스오버
- 거래량 가중 분석

## 개발 환경 설정

Poetry를 사용하여 개발 의존성 설치:
```bash
poetry install --with dev
```

코드 포맷팅:
```bash
poetry run black .
poetry run isort .
```

린팅:
```bash
poetry run flake8
poetry run mypy .
```

테스트 실행:
```bash
poetry run pytest
```

## ⚠️ 주의사항

- 이 봇은 실제 자금을 거래하므로 신중하게 사용하세요.
- 반드시 백테스팅을 충분히 수행한 후 실제 거래를 시작하세요.
- API 키는 절대로 공개되지 않도록 주의하세요.
- 모든 투자는 본인 책임 하에 이루어집니다.

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.