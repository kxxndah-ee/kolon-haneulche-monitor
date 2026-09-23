import sqlite3
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from config import settings

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    conn = get_connection()
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_hash TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            channel TEXT NOT NULL,
            source TEXT,
            author TEXT,
            published_at TEXT,
            collected_at TEXT NOT NULL,
            snippet TEXT,
            keyword TEXT,
            sentiment TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            detected_risks TEXT,
            is_read INTEGER DEFAULT 0,
            is_bookmarked INTEGER DEFAULT 0
        );
        """)
        
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_url_hash ON posts(url_hash);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_collected_at ON posts(collected_at DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_channel ON posts(channel);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_risk_level ON posts(risk_level);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_sentiment ON posts(sentiment);")
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS negative_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)
        
        # Populate initial default keywords if empty
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM keywords")
        if cur.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            for kw in settings.default_keywords:
                conn.execute(
                    "INSERT OR IGNORE INTO keywords (keyword, is_active, created_at) VALUES (?, 1, ?)",
                    (kw, now)
                )
                
        # Populate initial negative keywords if empty
        cur.execute("SELECT COUNT(*) FROM negative_keywords")
        if cur.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            for nkw in settings.negative_keywords:
                conn.execute(
                    "INSERT OR IGNORE INTO negative_keywords (keyword, created_at) VALUES (?, ?)",
                    (nkw, now)
                )

def compute_url_hash(url: str, title: str = "") -> str:
    norm_url = url.split("?")[0].strip().lower()
    if not norm_url or len(norm_url) < 10:
        norm_url = (url + "_" + title).strip().lower()
    return hashlib.sha256(norm_url.encode("utf-8")).hexdigest()

def insert_post(post_data: Dict[str, Any]) -> Optional[int]:
    """Insert post if not duplicate. Returns post id if inserted, None if duplicate."""
    url = post_data.get("url", "").strip()
    title = post_data.get("title", "").strip()
    if not url or not title:
        return None
        
    url_hash = compute_url_hash(url, title)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute("""
            INSERT OR IGNORE INTO posts (
                url_hash, title, url, channel, source, author,
                published_at, collected_at, snippet, keyword,
                sentiment, risk_level, risk_score, detected_risks,
                is_read, is_bookmarked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (
                url_hash,
                title,
                url,
                post_data.get("channel", "기타"),
                post_data.get("source", ""),
                post_data.get("author", ""),
                post_data.get("published_at", now[:10]),
                now,
                post_data.get("snippet", ""),
                post_data.get("keyword", ""),
                post_data.get("sentiment", "NEUTRAL"),
                post_data.get("risk_level", "SAFE"),
                post_data.get("risk_score", 0),
                json.dumps(post_data.get("detected_risks", []), ensure_ascii=False)
            ))
            if cursor.rowcount > 0:
                return cursor.lastrowid
            return None
    finally:
        conn.close()

def get_posts(
    channel: Optional[str] = None,
    risk_level: Optional[str] = None,
    sentiment: Optional[str] = None,
    search: Optional[str] = None,
    only_bookmarked: bool = False,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        query = "SELECT * FROM posts WHERE 1=1"
        params = []
        
        if channel and channel != "ALL":
            query += " AND channel = ?"
            params.append(channel)
        if risk_level and risk_level != "ALL":
            query += " AND risk_level = ?"
            params.append(risk_level)
        if sentiment and sentiment != "ALL":
            query += " AND sentiment = ?"
            params.append(sentiment)
        if only_bookmarked:
            query += " AND is_bookmarked = 1"
        if search:
            query += " AND (title LIKE ? OR snippet LIKE ? OR source LIKE ? OR keyword LIKE ?)"
            s_param = f"%{search}%"
            params.extend([s_param, s_param, s_param, s_param])
            
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("detected_risks"):
                try:
                    d["detected_risks"] = json.loads(d["detected_risks"])
                except Exception:
                    d["detected_risks"] = []
            result.append(d)
        return result
    finally:
        conn.close()

def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        total_posts = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        today_posts = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE collected_at LIKE ?",
            (f"{today_str}%",)
        ).fetchone()[0]
        
        high_risk_posts = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE risk_level = 'HIGH'"
        ).fetchone()[0]
        medium_risk_posts = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE risk_level = 'MEDIUM'"
        ).fetchone()[0]
        
        positive_posts = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE sentiment = 'POSITIVE'"
        ).fetchone()[0]
        negative_posts = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE sentiment = 'NEGATIVE'"
        ).fetchone()[0]
        neutral_posts = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE sentiment = 'NEUTRAL'"
        ).fetchone()[0]
        
        # Channel breakdown
        channels_rows = conn.execute(
            "SELECT channel, COUNT(*) as cnt FROM posts GROUP BY channel"
        ).fetchall()
        channels_dist = {r["channel"]: r["cnt"] for r in channels_rows}
        
        # Daily trend (last 7 days)
        trend_rows = conn.execute("""
            SELECT SUBSTR(collected_at, 1, 10) as dt, COUNT(*) as cnt
            FROM posts
            GROUP BY dt
            ORDER BY dt DESC
            LIMIT 7
        """).fetchall()
        trend = [{"date": r["dt"], "count": r["cnt"]} for r in reversed(trend_rows)]
        
        return {
            "total_posts": total_posts,
            "today_posts": today_posts,
            "high_risk_count": high_risk_posts,
            "medium_risk_count": medium_risk_posts,
            "positive_count": positive_posts,
            "negative_count": negative_posts,
            "neutral_count": neutral_posts,
            "channels_dist": channels_dist,
            "trend": trend
        }
    finally:
        conn.close()

def toggle_bookmark(post_id: int) -> bool:
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute("SELECT is_bookmarked FROM posts WHERE id = ?", (post_id,))
            row = cur.fetchone()
            if row:
                new_state = 0 if row[0] == 1 else 1
                conn.execute(
                    "UPDATE posts SET is_bookmarked = ? WHERE id = ?",
                    (new_state, post_id)
                )
                return bool(new_state)
            return False
    finally:
        conn.close()

def mark_as_read(post_id: int) -> bool:
    conn = get_connection()
    try:
        with conn:
            conn.execute("UPDATE posts SET is_read = 1 WHERE id = ?", (post_id,))
            return True
    finally:
        conn.close()

def get_keywords() -> List[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT keyword FROM keywords WHERE is_active = 1").fetchall()
        return [r["keyword"] for r in rows]
    finally:
        conn.close()

def add_keyword(keyword: str) -> bool:
    kw = keyword.strip()
    if not kw:
        return False
    conn = get_connection()
    try:
        with conn:
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO keywords (keyword, is_active, created_at) VALUES (?, 1, ?)",
                (kw, now)
            )
            return True
    finally:
        conn.close()

def delete_keyword(keyword: str) -> bool:
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM keywords WHERE keyword = ?", (keyword.strip(),))
            return True
    finally:
        conn.close()

def get_negative_keywords() -> List[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT keyword FROM negative_keywords").fetchall()
        return [r["keyword"] for r in rows]
    finally:
        conn.close()

def add_negative_keyword(keyword: str) -> bool:
    kw = keyword.strip()
    if not kw:
        return False
    conn = get_connection()
    try:
        with conn:
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT OR IGNORE INTO negative_keywords (keyword, created_at) VALUES (?, ?)",
                (kw, now)
            )
            return True
    finally:
        conn.close()

def delete_negative_keyword(keyword: str) -> bool:
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM negative_keywords WHERE keyword = ?", (keyword.strip(),))
            return True
    finally:
        conn.close()
