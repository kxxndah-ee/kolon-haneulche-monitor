import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import pandas as pd

from config import settings
from database import (
    init_db,
    get_posts,
    get_stats,
    toggle_bookmark,
    mark_as_read,
    get_keywords,
    add_keyword,
    delete_keyword,
    get_negative_keywords,
    add_negative_keyword,
    delete_negative_keyword
)
from scheduler import monitor_manager

app = FastAPI(title=settings.app_title, version=settings.app_version)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Startup event
@app.on_event("startup")
def on_startup():
    init_db()
    if settings.scheduler_enabled:
        monitor_manager.start(settings.default_interval_minutes)

@app.on_event("shutdown")
def on_shutdown():
    monitor_manager.stop()

# 1. UI Main Page
@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "app_title": settings.app_title})

# 2. Posts API
@app.get("/api/posts")
def api_get_posts(
    channel: Optional[str] = "ALL",
    risk_level: Optional[str] = "ALL",
    sentiment: Optional[str] = "ALL",
    search: Optional[str] = None,
    only_bookmarked: bool = False,
    limit: int = 100,
    offset: int = 0
):
    posts = get_posts(
        channel=channel,
        risk_level=risk_level,
        sentiment=sentiment,
        search=search,
        only_bookmarked=only_bookmarked,
        limit=limit,
        offset=offset
    )
    return {"posts": posts, "count": len(posts)}

@app.post("/api/posts/{post_id}/bookmark")
def api_toggle_bookmark(post_id: int):
    new_state = toggle_bookmark(post_id)
    return {"id": post_id, "is_bookmarked": new_state}

@app.post("/api/posts/{post_id}/read")
def api_mark_as_read(post_id: int):
    success = mark_as_read(post_id)
    return {"id": post_id, "success": success}

# 3. Statistics API
@app.get("/api/stats")
def api_get_stats():
    return get_stats()

# 4. Keywords API
class KeywordRequest(BaseModel):
    keyword: str

@app.get("/api/keywords")
def api_get_keywords():
    return {"keywords": get_keywords()}

@app.post("/api/keywords")
def api_add_keyword(req: KeywordRequest):
    success = add_keyword(req.keyword)
    return {"success": success, "keywords": get_keywords()}

@app.delete("/api/keywords/{keyword}")
def api_delete_keyword(keyword: str):
    success = delete_keyword(keyword)
    return {"success": success, "keywords": get_keywords()}

# 5. Negative Keywords API
@app.get("/api/negative-keywords")
def api_get_negative_keywords():
    return {"negative_keywords": get_negative_keywords()}

@app.post("/api/negative-keywords")
def api_add_negative_keyword(req: KeywordRequest):
    success = add_negative_keyword(req.keyword)
    return {"success": success, "negative_keywords": get_negative_keywords()}

@app.delete("/api/negative-keywords/{keyword}")
def api_delete_negative_keyword(keyword: str):
    success = delete_negative_keyword(keyword)
    return {"success": success, "negative_keywords": get_negative_keywords()}

# 6. Scheduler Controls
@app.get("/api/scheduler/status")
def api_scheduler_status():
    return {
        "is_running": monitor_manager.is_running,
        "is_collecting": monitor_manager.is_collecting,
        "last_run_time": monitor_manager.last_run_time,
        "last_new_count": monitor_manager.last_new_count,
        "current_interval": settings.default_interval_minutes
    }

@app.post("/api/scheduler/toggle")
def api_scheduler_toggle():
    if monitor_manager.is_running:
        monitor_manager.stop()
    else:
        monitor_manager.start(settings.default_interval_minutes)
    return {"is_running": monitor_manager.is_running}

class IntervalRequest(BaseModel):
    minutes: int

@app.post("/api/scheduler/interval")
def api_scheduler_interval(req: IntervalRequest):
    settings.default_interval_minutes = req.minutes
    monitor_manager.change_interval(req.minutes)
    return {"success": True, "interval": req.minutes}

@app.post("/api/scheduler/trigger")
def api_scheduler_trigger(background_tasks: BackgroundTasks):
    if monitor_manager.is_collecting:
        return {"status": "already_running", "message": "수집이 이미 진행 중입니다."}
    background_tasks.add_task(monitor_manager.run_once)
    return {"status": "started", "message": "실시간 수집 작업을 시작했습니다."}

# 7. Settings API
class SettingsUpdateRequest(BaseModel):
    toast_enabled: Optional[bool] = None
    telegram_enabled: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    naver_client_id: Optional[str] = None
    naver_client_secret: Optional[str] = None
    kakao_rest_api_key: Optional[str] = None

@app.get("/api/settings")
def api_get_settings():
    return {
        "toast_enabled": settings.toast_enabled,
        "telegram_enabled": settings.telegram_enabled,
        "telegram_bot_token": settings.telegram_bot_token,
        "telegram_chat_id": settings.telegram_chat_id,
        "naver_client_id": settings.naver_client_id,
        "naver_client_secret": settings.naver_client_secret,
        "kakao_rest_api_key": settings.kakao_rest_api_key,
        "default_interval_minutes": settings.default_interval_minutes
    }

@app.post("/api/settings")
def api_update_settings(req: SettingsUpdateRequest):
    if req.toast_enabled is not None:
        settings.toast_enabled = req.toast_enabled
    if req.telegram_enabled is not None:
        settings.telegram_enabled = req.telegram_enabled
    if req.telegram_bot_token is not None:
        settings.telegram_bot_token = req.telegram_bot_token
    if req.telegram_chat_id is not None:
        settings.telegram_chat_id = req.telegram_chat_id
    if req.naver_client_id is not None:
        settings.naver_client_id = req.naver_client_id
    if req.naver_client_secret is not None:
        settings.naver_client_secret = req.naver_client_secret
    if req.kakao_rest_api_key is not None:
        settings.kakao_rest_api_key = req.kakao_rest_api_key
    return {"success": True, "message": "설정이 성공적으로 저장되었습니다."}

# 8. Excel Export API
@app.get("/api/export/excel")
def api_export_excel(
    channel: Optional[str] = "ALL",
    risk_level: Optional[str] = "ALL",
    sentiment: Optional[str] = "ALL",
    search: Optional[str] = None
):
    posts = get_posts(
        channel=channel,
        risk_level=risk_level,
        sentiment=sentiment,
        search=search,
        limit=5000,
        offset=0
    )
    
    if not posts:
        raise HTTPException(status_code=404, detail="내보낼 게시글 데이터가 없습니다.")

    export_dir = BASE_DIR / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    filename = f"kolon_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    file_path = export_dir / filename

    rows = []
    for p in posts:
        rows.append({
            "ID": p["id"],
            "수집일시": p["collected_at"],
            "채널": p["channel"],
            "출처": p["source"],
            "작성자": p["author"],
            "작성일": p["published_at"],
            "타겟키워드": p["keyword"],
            "제목": p["title"],
            "원문링크": p["url"],
            "감성": p["sentiment"],
            "위험등급": p["risk_level"],
            "위험점수": p["risk_score"],
            "감지된위험어": ", ".join(p.get("detected_risks", [])) if isinstance(p.get("detected_risks"), list) else "",
            "본문요약": p["snippet"]
        })

    df = pd.DataFrame(rows)
    df.to_excel(str(file_path), index=False, engine="openpyxl")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# 9. Server-Sent Events (SSE) Live Feed
@app.get("/api/stream")
async def api_sse_stream():
    queue = asyncio.Queue()
    monitor_manager.sse_subscribers.append(queue)

    async def event_generator():
        try:
            # Send initial ping
            yield "data: {\"type\": \"connected\"}\n\n"
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in monitor_manager.sse_subscribers:
                monitor_manager.sse_subscribers.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.host, port=settings.port, reload=False)
