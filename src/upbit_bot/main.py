import logging
import os
import time
from datetime import datetime

from .strategy import MeanReversionStrategy, MomentumStrategy


def setup_logging():
    """로깅 설정"""
    # 로그 디렉토리 생성
    os.makedirs("logs", exist_ok=True)

    # 현재 날짜와 시간을 파일명에 포함
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/trading_{current_time}.log"
    trades_file = f"logs/trades_{current_time}.csv"

    # 로거 설정
    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    # 파일 핸들러
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 포맷 설정
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 거래 기록용 CSV 파일 헤더 생성
    with open(trades_file, "w") as f:
        f.write("datetime,action,price,amount,balance,fee,reason\n")

    return logger, trades_file


def run_live_trading(strategy_type="momentum", ticker="KRW-BTC", interval="minute60"):
    """실시간 거래 실행"""
    # 로거 설정
    logger, trades_file = setup_logging()

    # 전략 선택
    if strategy_type.lower() == "momentum":
        strategy = MomentumStrategy(
            ticker=ticker, interval=interval, logger=logger, trades_file=trades_file
        )
    else:
        strategy = MeanReversionStrategy(
            ticker=ticker, interval=interval, logger=logger, trades_file=trades_file
        )

    logger.info("=== 자동매매 시작 ===")
    logger.info(f"전략: {strategy_type}")
    logger.info(f"코인: {strategy.ticker}")
    logger.info(f"차트: {strategy.interval}")

    if isinstance(strategy, MomentumStrategy):
        logger.info(f"손절: {strategy.stop_loss_pct * 100}%")
        logger.info(f"1차 익절: {strategy.partial_profit_pct * 100}%")
        logger.info(f"2차 익절: {strategy.final_profit_pct * 100}%")
    else:
        logger.info(f"손절: {strategy.stop_loss_pct * 100}%")
        logger.info(f"익절: {strategy.take_profit_pct * 100}%")

    while True:
        try:
            # 시장 분석
            logger.debug("시장 분석 중...")
            signal, reason = strategy.analyze_market()

            # 매매 신호 발생 시 거래 실행
            if signal:
                logger.info(f"매매 신호 감지: {signal} ({reason})")
                strategy.execute_trade(signal, reason)

            # 대기 시간 설정
            interval_minutes = int(interval.replace("minute", ""))
            sleep_time = min(
                interval_minutes * 60 / 12, 300
            )  # 봉 길이의 1/12, 최대 5분
            logger.debug(f"다음 분석까지 {sleep_time}초 대기...")
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("=== 프로그램 종료 ===")
            break

        except Exception as e:
            logger.error(f"오류 발생: {str(e)}")
            time.sleep(60)  # 오류 발생 시 1분 대기 후 재시도


def main():
    """메인 실행 함수"""
    print("\n=== Upbit Trading Bot ===\n")

    # 전략 선택
    print("사용할 전략을 선택하세요:")
    print("1. 모멘텀 전략 (추세 추종)")
    print("2. 평균회귀 전략 (반추세)")

    while True:
        try:
            strategy_choice = input("\n선택 (1 또는 2): ").strip()
            if strategy_choice in ["1", "2"]:
                break
            print("잘못된 선택입니다. 1 또는 2를 입력하세요.")
        except ValueError:
            print("잘못된 입력입니다. 다시 시도하세요.")

    strategy_type = "momentum" if strategy_choice == "1" else "mean_reversion"

    # 거래 설정
    print("\n거래 설정:")
    ticker = input("코인 선택 (기본값: KRW-BTC): ").strip() or "KRW-BTC"

    print("\n차트 인터벌 선택:")
    print("1. 1분봉")
    print("2. 3분봉")
    print("3. 5분봉")
    print("4. 15분봉")
    print("5. 30분봉")
    print("6. 60분봉")

    interval_map = {
        "1": "minute1",
        "2": "minute3",
        "3": "minute5",
        "4": "minute15",
        "5": "minute30",
        "6": "minute60",
    }

    while True:
        try:
            interval_choice = input("\n선택 (1-6): ").strip()
            if interval_choice in interval_map:
                break
            print("잘못된 선택입니다. 1부터 6 사이의 숫자를 입력하세요.")
        except ValueError:
            print("잘못된 입력입니다. 다시 시도하세요.")

    interval = interval_map[interval_choice]

    # 설정 확인
    print("\n=== 설정 확인 ===")
    print(f"전략: {'모멘텀' if strategy_type == 'momentum' else '평균회귀'}")
    print(f"코인: {ticker}")
    print(f"차트: {interval}")

    confirm = input("\n시작하시겠습니까? (y/n): ").strip().lower()
    if confirm == "y":
        run_live_trading(strategy_type, ticker, interval)
    else:
        print("프로그램을 종료합니다.")


if __name__ == "__main__":
    main()
