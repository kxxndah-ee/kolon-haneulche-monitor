import logging
import urllib.parse
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from .base import BaseCollector

logger = logging.getLogger("kolon_monitor.news")

class NewsCollector(BaseCollector):
    def __init__(self):
        super().__init__("News")

    def collect(self, keyword: str) -> List[Dict[str, Any]]:
        posts = []
        # 1. Google News RSS
        try:
            posts.extend(self._collect_google_rss(keyword))
        except Exception as e:
            logger.error(f"Google News RSS error for '{keyword}': {e}")

        # 2. Daum News Search
        try:
            posts.extend(self._collect_daum_news(keyword))
        except Exception as e:
            logger.error(f"Daum News error for '{keyword}': {e}")

        return posts

    def _collect_google_rss(self, keyword: str) -> List[Dict[str, Any]]:
        q = urllib.parse.quote(keyword)
        url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
        results = []

        with self.get_client() as client:
            resp = client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "xml")
                for it in soup.find_all("item")[:30]:
                    full_title = it.title.text if it.title else ""
                    link = it.link.text if it.link else ""
                    pub_date = it.pubDate.text if it.pubDate else ""
                    desc = it.description.text if it.description else ""

                    # Usually "Title - MediaName"
                    media_name = "언론사"
                    title = full_title
                    if " - " in full_title:
                        parts = full_title.rsplit(" - ", 1)
                        title = parts[0]
                        media_name = parts[1]

                    clean_desc = re.sub(r"<[^>]+>", "", desc)
                    results.append({
                        "title": title,
                        "url": link,
                        "channel": "뉴스",
                        "source": media_name,
                        "author": "",
                        "published_at": pub_date,
                        "snippet": clean_desc[:150],
                        "keyword": keyword
                    })
        return results

    def _collect_daum_news(self, keyword: str) -> List[Dict[str, Any]]:
        q = urllib.parse.quote(keyword)
        url = f"https://search.daum.net/search?w=news&q={q}&sort=recency"
        headers = {"Referer": "https://www.daum.net/"}
        results = []

        with self.get_client(headers) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                seen_urls = set()
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    if "v.daum.net/v/" in href and href not in seen_urls:
                        text = a.get_text(strip=True)
                        if len(text) > 8:
                            seen_urls.add(href)
                            results.append({
                                "title": text,
                                "url": href,
                                "channel": "뉴스",
                                "source": "다음뉴스",
                                "author": "",
                                "published_at": "",
                                "snippet": "",
                                "keyword": keyword
                            })
        return results
