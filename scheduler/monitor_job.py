import logging
import asyncio
import threading
from datetime import datetime
from typing import List, Dict, Any, Callable
from apscheduler.schedulers.background import BackgroundScheduler

from config import settings
from database import (
    get_keywords,
    get_negative_keywords,
    insert_post
)
from analyzer import analyze_text
from collectors import (
    NaverCafeCollector,
    NaverBlogCollector,
    DaumCollector,
    CommunityCollector,
    NewsCollector
)
from notifier import show_toast, send_telegram_alert

logger = logging.getLogger("kolon_monitor.scheduler")

class MonitorJobManager:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="Asia/Seoul")
        self.collectors = [
            NaverCafeCollector(),
            NaverBlogCollector(),
            DaumCollector(),
            CommunityCollector(),
            NewsCollector()
        ]
        self.is_running = False
        self.is_collecting = False
        self.last_run_time: str = ""
        self.last_new_count: int = 0
        self.sse_subscribers: List[asyncio.Queue] = []
        self._lock = threading.Lock()

    def start(self, interval_minutes: int = 15):
        if not self.scheduler.running:
            self.scheduler.add_job(
                self.run_once,
                "interval",
                minutes=interval_minutes,
                id="kolon_monitor_job",
                replace_existing=True
            )
            self.scheduler.start()
            self.is_running = True
            logger.info(f"Scheduler started with interval {interval_minutes}m")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.remove_job("kolon_monitor_job")
            self.is_running = False
            logger.info("Scheduler stopped")

    def change_interval(self, minutes: int):
        if self.scheduler.running and self.scheduler.get_job("kolon_monitor_job"):
            self.scheduler.reschedule_job(
                "kolon_monitor_job",
                trigger="interval",
                minutes=minutes
            )
            logger.info(f"Rescheduled job interval to {minutes}m")

    def run_once(self) -> int:
        """Executes a single monitoring cycle synchronously across all keywords and collectors."""
        with self._lock:
            if self.is_collecting:
                logger.info("Collection cycle already in progress, skipping...")
                return 0
            self.is_collecting = True

        logger.info("Starting monitoring cycle...")
        new_posts_count = 0
        self.last_run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            keywords = get_keywords()
            negative_keywords = get_negative_keywords()

            for kw in keywords:
                for col in self.collectors:
                    try:
                        raw_items = col.collect(kw)
                        for item in raw_items:
                            analysis = analyze_text(
                                title=item.get("title", ""),
                                snippet=item.get("snippet", ""),
                                negative_keywords=negative_keywords
                            )

                            if analysis.get("is_noise"):
                                continue

                            post_dict = {
                                **item,
                                "sentiment": analysis.get("sentiment"),
                                "risk_level": analysis.get("risk_level"),
                                "risk_score": analysis.get("risk_score"),
                                "detected_risks": analysis.get("detected_risks")
                            }

                            post_id = insert_post(post_dict)
                            if post_id is not None:
                                new_posts_count += 1
                                post_dict["id"] = post_id
                                
                                # Send notifications for risk posts
                                risk_level = post_dict.get("risk_level")
                                if risk_level in ["HIGH", "MEDIUM"]:
                                    if settings.toast_enabled:
                                        show_toast(
                                            title=f"[{item.get('channel')}] {item.get('title')}",
                                            message=f"리스크 감지: {', '.join(analysis.get('detected_risks', []))}",
                                            risk_level=risk_level
                                        )
                                    if settings.telegram_enabled and settings.telegram_bot_token:
                                        send_telegram_alert(
                                            bot_token=settings.telegram_bot_token,
                                            chat_id=settings.telegram_chat_id,
                                            title=item.get("title", ""),
                                            channel=item.get("channel", ""),
                                            url=item.get("url", ""),
                                            risk_level=risk_level,
                                            snippet=item.get("snippet", "")
                                        )

                                # Broadcast to SSE queues if any
                                self._broadcast_new_post(post_dict)
                    except Exception as e:
                        logger.error(f"Collector {col.name} failed for keyword '{kw}': {e}")

            self.last_new_count = new_posts_count
            logger.info(f"Monitoring cycle finished. Found {new_posts_count} new posts.")
            return new_posts_count
        finally:
            with self._lock:
                self.is_collecting = False

    def _broadcast_new_post(self, post_data: Dict[str, Any]):
        for q in self.sse_subscribers:
            try:
                q.put_nowait(post_data)
            except Exception:
                pass

monitor_manager = MonitorJobManager()
