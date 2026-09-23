import logging
import urllib.parse
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from .base import BaseCollector

logger = logging.getLogger("kolon_monitor.community")

COMMUNITY_DOMAINS = {
    "ppomppu.co.kr": "뽐뿌",
    "dcinside.com": "디시인사이드",
    "clien.net": "클리앙",
    "fmkorea.com": "에펨코리아",
    "teamblind.com": "블라인드",
    "arca.live": "아카라이브",
    "bobaedream.co.kr": "보배드림",
    "inven.co.kr": "인벤",
    "ruliweb.com": "루리웹"
}

class CommunityCollector(BaseCollector):
    def __init__(self):
        super().__init__("Community")

    def collect(self, keyword: str) -> List[Dict[str, Any]]:
        posts = []
        try:
            site_queries = " OR ".join([f"site:{dom}" for dom in list(COMMUNITY_DOMAINS.keys())[:6]])
            full_query = f"{keyword} ({site_queries})"
            encoded_query = urllib.parse.quote(full_query)
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"

            with self.get_client() as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "xml")
                    items = soup.find_all("item")
                    for it in items:
                        title = it.title.text if it.title else ""
                        link = it.link.text if it.link else ""
                        pub_date = it.pubDate.text if it.pubDate else ""
                        desc = it.description.text if it.description else ""

                        # Identify community source name
                        matched_source = "커뮤니티"
                        for dom, name in COMMUNITY_DOMAINS.items():
                            if dom in link or dom in title:
                                matched_source = name
                                break
                                
                        clean_desc = re.sub(r"<[^>]+>", "", desc)
                        posts.append({
                            "title": title,
                            "url": link,
                            "channel": "커뮤니티",
                            "source": matched_source,
                            "author": "",
                            "published_at": pub_date,
                            "snippet": clean_desc[:150],
                            "keyword": keyword
                        })
        except Exception as e:
            logger.error(f"Community collector error for '{keyword}': {e}")

        return posts
