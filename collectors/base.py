import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import httpx

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from config import settings

logger = logging.getLogger("kolon_monitor.collector")

class BaseCollector(ABC):
    def __init__(self, name: str):
        self.name = name
        self.headers = {
            "User-Agent": settings.user_agent,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }
        self.timeout = settings.request_timeout

    def get_client(self, extra_headers: Dict[str, str] = None) -> httpx.Client:
        h = dict(self.headers)
        if extra_headers:
            h.update(extra_headers)
        return httpx.Client(headers=h, timeout=self.timeout, follow_redirects=True)

    @abstractmethod
    def collect(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Collects posts for the given keyword.
        Must return a list of dicts:
        {
            'title': str,
            'url': str,
            'channel': str,  # '네이버 카페', '네이버 블로그', '다음 카페', etc.
            'source': str,   # e.g. cafe name, blog name, media name
            'author': str,
            'published_at': str,
            'snippet': str,
            'keyword': str
        }
        """
        pass
