from datetime import datetime, timezone
from typing import Optional, Dict, Any
from src.config import config


def _get(d: Optional[dict], *keys) -> Any:
    """Lấy giá trị đầu tiên tìm thấy từ danh sách keys dự phòng."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def get_task_config(quest: dict) -> Optional[dict]:
    """Trích xuất cấu hình task của quest (ưu tiên task_config_v2 mới nhất)."""
    cfg = quest.get("config", {})
    if not isinstance(cfg, dict):
        return None
    v2 = _get(cfg, "taskConfigV2", "task_config_v2")
    if v2 and isinstance(v2, dict) and v2.get("tasks"):
        return v2
    return _get(cfg, "taskConfig", "task_config", "taskConfigV2", "task_config_v2")


def get_app_id(quest: dict) -> Optional[str]:
    """Lấy application ID liên quan đến quest / task."""
    tc = get_task_config(quest)
    task_type = get_task_type(quest)
    if tc and task_type and isinstance(tc.get("tasks"), dict):
        task_info = tc["tasks"].get(task_type, {})
        if isinstance(task_info, dict):
            apps = task_info.get("applications", [])
            if apps and isinstance(apps, list) and isinstance(apps[0], dict):
                app_id = apps[0].get("id")
                if app_id:
                    return str(app_id)
    cfg = quest.get("config", {})
    if isinstance(cfg, dict):
        app = cfg.get("application", {})
        if isinstance(app, dict) and app.get("id"):
            return str(app["id"])
    return None


def get_quest_name(quest: dict) -> str:
    """Lấy tên hiển thị của quest hoặc tiêu đề game."""
    cfg = quest.get("config", {})
    if isinstance(cfg, dict):
        msgs = cfg.get("messages", {})
        if isinstance(msgs, dict):
            name = _get(msgs, "questName", "quest_name") or _get(msgs, "gameTitle", "game_title")
            if name:
                return str(name)
    return f"Quest#{quest.get('id', 'Unknown')}"


def get_user_status(quest: dict) -> dict:
    """Lấy trạng thái người dùng đối với quest."""
    us = _get(quest, "userStatus", "user_status")
    return us if isinstance(us, dict) else {}


def is_enrolled(quest: dict) -> bool:
    """Kiểm tra tài khoản đã nhận quest hay chưa."""
    return bool(_get(get_user_status(quest), "enrolledAt", "enrolled_at"))


def is_completed(quest: dict) -> bool:
    """Kiểm tra quest đã đạt 100% tiến độ chưa."""
    return bool(_get(get_user_status(quest), "completedAt", "completed_at"))


def is_claimed(quest: dict) -> bool:
    """Kiểm tra quest đã nhận thưởng (claim reward) chưa."""
    return bool(_get(get_user_status(quest), "claimedAt", "claimed_at"))


def is_expired(quest: dict) -> bool:
    """Kiểm tra quest đã hết hạn chưa."""
    cfg = quest.get("config", {})
    if not isinstance(cfg, dict):
        return False
    expires_at_str = _get(cfg, "expiresAt", "expires_at")
    if not expires_at_str:
        return False
    try:
        expires_at = datetime.fromisoformat(str(expires_at_str).replace("Z", "+00:00"))
        return expires_at <= datetime.now(timezone.utc)
    except Exception:
        return False


def has_started(quest: dict) -> bool:
    """Kiểm tra quest đã bắt đầu chưa."""
    cfg = quest.get("config", {})
    if not isinstance(cfg, dict):
        return True
    starts_at_str = _get(cfg, "startsAt", "starts_at")
    if not starts_at_str:
        return True
    try:
        starts_at = datetime.fromisoformat(str(starts_at_str).replace("Z", "+00:00"))
        return starts_at <= datetime.now(timezone.utc)
    except Exception:
        return True


def is_active(quest: dict) -> bool:
    """Kiểm tra quest có đang trong thời gian hiệu lực (đã bắt đầu và chưa hết hạn)."""
    return has_started(quest) and not is_expired(quest)


def get_task_type(quest: dict) -> Optional[str]:
    """Xác định loại nhiệm vụ (WATCH_VIDEO, PLAY_ON_DESKTOP, v.v.)."""
    tc = get_task_config(quest)
    if not tc or "tasks" not in tc or not isinstance(tc["tasks"], dict):
        return None
    for t in config.supported_tasks:
        if tc["tasks"].get(t) is not None:
            return t
    return None


def get_seconds_needed(quest: dict) -> int:
    """Lấy tổng thời gian (giây) cần hoàn thành."""
    tc = get_task_config(quest)
    task_type = get_task_type(quest)
    if tc and task_type and isinstance(tc.get("tasks"), dict):
        task_info = tc["tasks"].get(task_type, {})
        if isinstance(task_info, dict):
            return int(task_info.get("target", 0))
    return 0


def get_seconds_done(quest: dict) -> float:
    """Lấy số giây đã hoàn thành hiện tại."""
    task_type = get_task_type(quest)
    if not task_type:
        return 0.0
    progress = get_user_status(quest).get("progress", {}) or {}
    if isinstance(progress, dict) and task_type in progress:
        val = progress[task_type].get("value", 0)
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0
    return 0.0
