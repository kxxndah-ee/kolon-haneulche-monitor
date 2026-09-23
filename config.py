import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DATA_DIR / "kolon_monitor.db")

class Settings(BaseModel):
    # App
    app_title: str = "코오롱글로벌·하늘채 커뮤니티 통합 모니터링 시스템"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    db_path: str = DB_PATH
    
    # Target Keywords
    default_keywords: List[str] = [
        "코오롱글로벌",
        "코오롱 하늘채",
        "하늘채",
        "코오롱건설",
        "산곡역 자이힐스하늘채",
        "엄궁역 트라비스 하늘채",
        "금정산 하늘채",
        "대전 하늘채 스카이앤",
        "수원 하늘채 더퍼스트"
    ]
    
    # Negative Keywords (Noise Filtering: restaurants, pensions, unrelated food stores)
    negative_keywords: List[str] = [
        "한정식", "쌈밥", "고깃집", "삼겹살", "갈비", "맛집", "식당",
        "칼국수", "순대국", "펜션", "모텔", "카페라떼", "아메리카노",
        "디저트", "베이커리", "글램핑", "캠핑장", "원룸텔", "고시원"
    ]
    
    # Monitoring Scheduler
    scheduler_enabled: bool = True
    default_interval_minutes: int = 15  # 5, 15, 30, 60
    
    # Windows Toast Notification
    toast_enabled: bool = True
    toast_min_risk_level: str = "MEDIUM"  # "LOW", "MEDIUM", "HIGH"
    
    # Telegram Bot
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    # Optional Official Open APIs
    naver_client_id: str = ""
    naver_client_secret: str = ""
    kakao_rest_api_key: str = ""
    
    # HTTP Crawling Settings
    request_timeout: float = 12.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

settings = Settings()
