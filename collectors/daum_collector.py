import logging
import urllib.parse
import json
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from .base import BaseCollector
from config import settings

logger = logging.getLogger("kolon_monitor.daum")

class DaumCollector(BaseCollector):
    def __init__(self):
        super().__init__("Daum")

    def collect(self, keyword: str) -> List[Dict[str, Any]]:
        posts = []
        # 1. Try Kakao Official API if configured
        if settings.kakao_rest_api_key:
            try:
                posts.extend(self._collect_via_kakao_api(keyword, "cafe"))
                posts.extend(self._collect_via_kakao_api(keyword, "blog"))
            except Exception as e:
                logger.error(f"Kakao API error: {e}")

        # 2. Web search crawling for cafe, blog, board
        for col, channel_name in [("cafe", "다음 카페"), ("blog", "다음 블로그"), ("board", "커뮤니티")]:
            try:
                col_posts = self._collect_via_web(keyword, col, channel_name)
                posts.extend(col_posts)
            except Exception as e:
                logger.error(f"Daum {col} error for '{keyword}': {e}")

        return posts

    def _collect_via_web(self, keyword: str, col: str, channel_name: str) -> List[Dict[str, Any]]:
        q = urllib.parse.quote(keyword)
        url = f"https://search.daum.net/search?w=fusion&col={col}&q={q}&sort=recency"
        headers = {"Referer": "https://www.daum.net/"}
        results = []

        with self.get_client(headers) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("c-card")

            seen_urls = set()
            for card in cards:
                title = ""
                post_url = ""
                snippet = ""
                source = channel_name
                date_str = ""

                # 1. First priority: parse embedded JSON
                script_tag = card.find("script", type="application/json")
                if script_tag and script_tag.string:
                    try:
                        d = json.loads(script_tag.string)
                        data_part = d.get("data", {})
                        title = data_part.get("TITLE") or d.get("prefix", "")
                        post_url = data_part.get("TH_WEB_URL_0") or d.get("link", "")
                        snippet = data_part.get("DESCRIPTION") or ""
                        source = d.get("service_name") or channel_name
                    except Exception:
                        pass

                # 2. Fallback to web component tags
                if not post_url:
                    title_el = card.find("c-title") or card.find("c-header-item")
                    if title_el:
                        title = title or title_el.get_text(strip=True)
                        post_url = title_el.get("data-href") or ""
                    
                if not snippet:
                    desc_el = card.find("c-contents-desc")
                    if desc_el:
                        snippet = desc_el.get_text(strip=True)

                bread_el = card.find("c-breadcrumb")
                if bread_el:
                    frags = bread_el.find_all("c-frag")
                    if len(frags) > 1:
                        source = frags[1].get_text(strip=True)

                footer_el = card.find("c-footer-desc")
                if footer_el:
                    date_str = footer_el.get_text(strip=True)

                if post_url and post_url not in seen_urls and len(title) > 2:
                    seen_urls.add(post_url)
                    results.append({
                        "title": re.sub(r"<[^>]+>", "", title),
                        "url": post_url,
                        "channel": channel_name,
                        "source": source,
                        "author": "",
                        "published_at": date_str,
                        "snippet": re.sub(r"<[^>]+>", "", snippet),
                        "keyword": keyword
                    })

        return results

    def _collect_via_kakao_api(self, keyword: str, target: str) -> List[Dict[str, Any]]:
        endpoint = f"https://dapi.kakao.com/v2/search/{target}"
        headers = {"Authorization": f"KakaoAK {settings.kakao_rest_api_key}"}
        params = {"query": keyword, "sort": "recency", "size": 30}
        
        channel_name = "다음 카페" if target == "cafe" else "다음 블로그"
        results = []
        with self.get_client(headers) as client:
            resp = client.get(endpoint, params=params)
            if resp.status_code == 200:
                data = resp.json()
                for doc in data.get("documents", []):
                    results.append({
                        "title": re.sub(r"<[^>]+>", "", doc.get("title", "")),
                        "url": doc.get("url", ""),
                        "channel": channel_name,
                        "source": doc.get("cafename") or doc.get("blogname") or channel_name,
                        "author": "",
                        "published_at": (doc.get("datetime") or "")[:10],
                        "snippet": re.sub(r"<[^>]+>", "", doc.get("contents", "")),
                        "keyword": keyword
                    })
        return results
