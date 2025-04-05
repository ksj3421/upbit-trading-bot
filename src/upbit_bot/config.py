import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Upbit API 설정
UPBIT_ACCESS_KEY = os.getenv('UPBIT_ACCESS_KEY', '')
UPBIT_SECRET_KEY = os.getenv('UPBIT_SECRET_KEY', '')

# 로깅 설정
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'