import requests
from datetime import datetime, timezone
from typing import Optional, List, Dict
from src.config import config
from src.utils.logger import log


def send_webhook(
    title: str,
    description: str,
    color: int = 0x5865F2,
    fields: Optional[List[Dict[str, str]]] = None,
    webhook_url: Optional[str] = None
) -> bool:
    url = (webhook_url or config.discord_webhook_url).strip()
    if not url:
        return False

    try:
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {
                "text": "Discord Quest Auto-Completer v4.0 PRO"
            }
        }
        if fields:
            embed["fields"] = fields

        payload = {
            "username": "Quest Auto-Completer",
            "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
            "embeds": [embed]
        }
        
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            return True
        else:
            log(f"Lỗi gửi Webhook ({resp.status_code}): {resp.text[:100]}", "warn")
            return False
    except Exception as e:
        log(f"Lỗi kết nối Webhook: {e}", "warn")
        return False


def test_webhook() -> bool:
    if not config.discord_webhook_url:
        log("Chưa cấu hình 'discord_webhook_url' trong config.json", "warn")
        return False
    log("Đang kiểm tra kết nối Discord Webhook...", "info")
    success = send_webhook(
        title="🔔 Kiểm Tra Kết Nối Thành Công!",
        description="Bot thông báo Quest Auto-Completer đã kết nối với kênh Discord của bạn thành công.",
        color=0x00FF7F,
        fields=[
            {"name": "Trạng thái", "value": "Sẵn sàng hoạt động", "inline": True},
            {"name": "Phiên bản", "value": "v4.0 PRO", "inline": True}
        ]
    )
    if success:
        log("Gửi thông báo thử nghiệm Webhook thành công!", "ok")
    else:
        log("Gửi thông báo thử nghiệm Webhook thất bại!", "error")
    return success
