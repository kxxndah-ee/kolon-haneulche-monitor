import logging
import httpx
from typing import Optional

logger = logging.getLogger("kolon_monitor.telegram")

def send_telegram_alert(
    bot_token: str,
    chat_id: str,
    title: str,
    channel: str,
    url: str,
    risk_level: str,
    snippet: str = ""
) -> bool:
    """Sends an alert message to a Telegram chat or channel."""
    if not bot_token or not chat_id:
        return False

    icon = "🚨" if risk_level == "HIGH" else "⚠️"
    text = (
        f"{icon} <b>[코오롱글로벌·하늘채 모니터링 알림]</b>\n\n"
        f"<b>등급:</b> {risk_level}\n"
        f"<b>채널:</b> {channel}\n"
        f"<b>제목:</b> {title}\n"
        f"<b>링크:</b> {url}\n"
    )
    if snippet:
        text += f"\n<b>내용 요약:</b>\n{snippet[:200]}"

    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(endpoint, json=payload)
            if resp.status_code == 200:
                return True
            else:
                logger.warning(f"Telegram API responded with {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False
