import logging
import urllib.parse
import json
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from .base import BaseCollector
from config import settings

logger = logging.getLogger("kolon_monitor.naver")

class NaverCafeCollector(BaseCollector):
    def __init__(self):
        super().__init__("NaverCafe")

    def collect(self, keyword: str) -> List[Dict[str, Any]]:
        posts = []
        # 1. Try official API if configured
        if settings.naver_client_id and settings.naver_client_secret:
            try:
                api_posts = self._collect_via_api(keyword)
                posts.extend(api_posts)
            except Exception as e:
                logger.error(f"Naver Cafe API error: {e}")

        # 2. Web search crawling (ssc=tab.cafe.all with date sort)
        try:
            web_posts = self._collect_via_web(keyword)
            posts.extend(web_posts)
        except Exception as e:
            logger.error(f"Naver Cafe web search error for '{keyword}': {e}")

        return posts

    def _collect_via_web(self, keyword: str) -> List[Dict[str, Any]]:
        q = urllib.parse.quote(keyword)
        url = f"https://search.naver.com/search.naver?ssc=tab.cafe.all&query={q}&sm=tab_opt&nso=so:dd"
        
        results = []
        with self.get_client() as client:
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning(f"Naver Cafe returned status {resp.status_code}")
                return results

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".view_wrap, .bx, li[data-cr-area]")

            seen_urls = set()
            for item in items:
                title_el = item.select_one("a.title_link, a.api_txt_lines")
                if not title_el:
                    continue
                
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)

                desc_el = item.select_one(".dsc_link, .dsc_txt, .api_txt_lines.dsc_txt")
                source_el = item.select_one(".name, .sub_txt, .source")
                date_el = item.select_one(".sub_time, .txt_date, .info")

                snippet = desc_el.get_text(strip=True) if desc_el else ""
                source = source_el.get_text(strip=True) if source_el else "네이버 카페"
                date_str = date_el.get_text(strip=True) if date_el else ""

                results.append({
                    "title": title,
                    "url": href,
                    "channel": "네이버 카페",
                    "source": source,
                    "author": "",
                    "published_at": date_str,
                    "snippet": snippet,
                    "keyword": keyword
                })

        return results

    def _collect_via_api(self, keyword: str) -> List[Dict[str, Any]]:
        url = f"https://openapi.naver.com/v1/search/cafearticle.json?query={urllib.parse.quote(keyword)}&display=30&sort=date"
        headers = {
            "X-Naver-Client-Id": settings.naver_client_id,
            "X-Naver-Client-Secret": settings.naver_client_secret
        }
        results = []
        with self.get_client(headers) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for it in data.get("items", []):
                    clean_title = re.sub(r"<[^>]+>", "", it.get("title", ""))
                    clean_desc = re.sub(r"<[^>]+>", "", it.get("description", ""))
                    results.append({
                        "title": clean_title,
                        "url": it.get("link", ""),
                        "channel": "네이버 카페",
                        "source": it.get("cafename", "네이버 카페"),
                        "author": "",
                        "published_at": "",
                        "snippet": clean_desc,
                        "keyword": keyword
                    })
        return results


class NaverBlogCollector(BaseCollector):
    def __init__(self):
        super().__init__("NaverBlog")

    def collect(self, keyword: str) -> List[Dict[str, Any]]:
        posts = []
        # 1. Try official API if configured
        if settings.naver_client_id and settings.naver_client_secret:
            try:
                posts.extend(self._collect_via_api(keyword))
            except Exception as e:
                logger.error(f"Naver Blog API error: {e}")

        # 2. Section Blog AJAX Search
        try:
            posts.extend(self._collect_via_section_blog(keyword))
        except Exception as e:
            logger.debug(f"Section Blog error: {e}")

        # 3. Web Search (ssc=tab.blog.all with date sort)
        try:
            posts.extend(self._collect_via_web(keyword))
        except Exception as e:
            logger.error(f"Naver Blog web search error for '{keyword}': {e}")

        return posts

    def _collect_via_section_blog(self, keyword: str) -> List[Dict[str, Any]]:
        url = (
            f"https://section.blog.naver.com/ajax/SearchList.naver?"
            f"countPerPage=30&currentPage=1&keyword={urllib.parse.quote(keyword)}&orderBy=recentdate&type=post"
        )
        headers = {"Referer": "https://section.blog.naver.com/"}
        results = []
        with self.get_client(headers) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                raw_text = resp.text.replace(")]}',", "").strip()
                data = json.loads(raw_text)
                items = data.get("result", {}).get("searchList", [])
                for it in items:
                    clean_title = re.sub(r"<[^>]+>", "", it.get("title", ""))
                    clean_desc = re.sub(r"<[^>]+>", "", it.get("contents", ""))
                    results.append({
                        "title": clean_title,
                        "url": it.get("postUrl", ""),
                        "channel": "네이버 블로그",
                        "source": it.get("blogName", "네이버 블로그"),
                        "author": it.get("nickName", ""),
                        "published_at": it.get("addDate", ""),
                        "snippet": clean_desc,
                        "keyword": keyword
                    })
        return results

    def _collect_via_web(self, keyword: str) -> List[Dict[str, Any]]:
        q = urllib.parse.quote(keyword)
        url = f"https://search.naver.com/search.naver?ssc=tab.blog.all&query={q}&sm=tab_opt&nso=so:dd"
        results = []
        with self.get_client() as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".view_wrap, .bx, li[data-cr-area]")

            seen = set()
            for item in items:
                title_el = item.select_one("a.title_link, a.api_txt_lines")
                if not title_el:
                    continue
                href = title_el.get("href", "")
                if not href or href in seen:
                    continue
                seen.add(href)

                desc_el = item.select_one(".dsc_link, .dsc_txt, .api_txt_lines.dsc_txt")
                source_el = item.select_one(".name, .sub_txt, .source")
                date_el = item.select_one(".sub_time, .txt_date, .info")

                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": href,
                    "channel": "네이버 블로그",
                    "source": source_el.get_text(strip=True) if source_el else "네이버 블로그",
                    "author": "",
                    "published_at": date_el.get_text(strip=True) if date_el else "",
                    "snippet": desc_el.get_text(strip=True) if desc_el else "",
                    "keyword": keyword
                })
        return results

    def _collect_via_api(self, keyword: str) -> List[Dict[str, Any]]:
        url = f"https://openapi.naver.com/v1/search/blog.json?query={urllib.parse.quote(keyword)}&display=30&sort=date"
        headers = {
            "X-Naver-Client-Id": settings.naver_client_id,
            "X-Naver-Client-Secret": settings.naver_client_secret
        }
        results = []
        with self.get_client(headers) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for it in data.get("items", []):
                    results.append({
                        "title": re.sub(r"<[^>]+>", "", it.get("title", "")),
                        "url": it.get("link", ""),
                        "channel": "네이버 블로그",
                        "source": it.get("bloggername", "네이버 블로그"),
                        "author": "",
                        "published_at": it.get("postdate", ""),
                        "snippet": re.sub(r"<[^>]+>", "", it.get("description", "")),
                        "keyword": keyword
                    })
        return results
