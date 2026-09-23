import sys
import os
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analyzer import analyze_text, is_noise
from database import (
    init_db,
    insert_post,
    get_posts,
    get_stats,
    toggle_bookmark,
    get_keywords,
    add_keyword,
    delete_keyword
)

class TestKolonMonitor(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_sentiment_high_risk(self):
        title = "코오롱 하늘채 신축 아파트 지하주차장 심각한 누수 및 균열 발생 비대위 결성"
        res = analyze_text(title, "주민들 분통")
        self.assertEqual(res["risk_level"], "HIGH")
        self.assertEqual(res["sentiment"], "NEGATIVE")
        self.assertGreaterEqual(res["risk_score"], 80)
        self.assertIn("누수", res["detected_risks"])
        self.assertIn("균열", res["detected_risks"])

    def test_sentiment_medium_risk(self):
        title = "하늘채 입주예정자 사전점검 타일 마감불량 하자 및 공사소음 민원"
        res = analyze_text(title, "")
        self.assertEqual(res["risk_level"], "MEDIUM")
        self.assertEqual(res["sentiment"], "NEGATIVE")
        self.assertGreaterEqual(res["risk_score"], 50)
        self.assertIn("하자", res["detected_risks"])

    def test_sentiment_positive(self):
        title = "코오롱글로벌 대전 하늘채 스카이앤 프리미엄 랜드마크 우수시공 완판 성공"
        res = analyze_text(title, "")
        self.assertEqual(res["sentiment"], "POSITIVE")
        self.assertEqual(res["risk_level"], "INFO")

    def test_noise_filtering(self):
        # Noise without real estate context
        title = "주말에 다녀온 하늘채 한정식 쌈밥 맛집 솔직 후기"
        res = analyze_text(title, "갈비탕도 맛있어요", negative_keywords=["한정식", "쌈밥", "맛집"])
        self.assertTrue(res["is_noise"])

    def test_database_dedup(self):
        import time
        unique_url = f"https://cafe.naver.com/sample/{int(time.time()*1000)}"
        post_data = {
            "title": "테스트 하늘채 분양 소식",
            "url": unique_url,
            "channel": "네이버 카페",
            "source": "부동산카페",
            "author": "작성자",
            "published_at": "2026-09-23",
            "snippet": "테스트 내용입니다.",
            "keyword": "하늘채",
            "sentiment": "NEUTRAL",
            "risk_level": "SAFE",
            "risk_score": 0,
            "detected_risks": []
        }
        # First insert
        post_id_1 = insert_post(post_data)
        self.assertIsNotNone(post_id_1)

        # Duplicate insert
        post_id_2 = insert_post(post_data)
        self.assertIsNone(post_id_2)

        # Check retrieval
        posts = get_posts(search="테스트 하늘채")
        self.assertTrue(len(posts) >= 1)

        # Bookmark toggle
        new_state = toggle_bookmark(post_id_1)
        self.assertTrue(new_state)

if __name__ == "__main__":
    unittest.main()
