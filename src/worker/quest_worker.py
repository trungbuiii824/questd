import time
import random
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List, Set

import urllib.parse
import requests

from src.config import config
from src.discord.api import DiscordAPI
from src.discord.models import (
    _get,
    get_task_config,
    get_app_id,
    get_quest_name,
    get_user_status,
    is_enrolled,
    is_completed,
    is_claimed,
    is_expired,
    has_started,
    is_active,
    get_task_type,
    get_seconds_needed,
    get_seconds_done,
)
from src.utils.logger import Colors, log
from src.utils.notifier import send_webhook

_rewards_lock = threading.Lock()


class QuestWorker:
    def __init__(
        self,
        api: DiscordAPI,
        on_progress=None,
        on_quest_complete=None,
        on_status=None,
    ):
        self.api = api
        self.completed_ids: Set[str] = set()
        self._lock = threading.Lock()
        self.on_progress = on_progress
        self.on_quest_complete = on_quest_complete
        self.on_status = on_status

    def fetch_quests(self) -> list:
        """Lấy danh sách các quest khả dụng của tài khoản."""
        try:
            r = self.api.get("/quests/@me")
            if r.status_code == 200:
                data = r.json()
                return data.get("quests", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            elif r.status_code == 429:
                wait = r.json().get("retry_after", 10)
                log(f"Bị giới hạn tốc độ (Rate Limit). Chờ {wait}s...", "warn", self.api.username)
                time.sleep(wait + 1)
                return self.fetch_quests()
            else:
                log(f"Không thể lấy danh sách quest (HTTP {r.status_code}): {r.text[:100]}", "warn", self.api.username)
                return []
        except Exception as e:
            log(f"Lỗi khi lấy quest: {e}", "error", self.api.username)
            return []

    def enroll(self, quest: dict) -> bool:
        """Nhận quest mới (Enroll)."""
        qid = quest["id"]
        name = get_quest_name(quest)

        if is_expired(quest):
            log(f"Bỏ qua quest [{name}] do đã hết hạn.", "warn", self.api.username)
            return False

        if not has_started(quest):
            log(f"Bỏ qua quest [{name}] do chưa bắt đầu.", "info", self.api.username)
            return False

        try:
            r = self.api.post(f"/quests/{qid}/enroll", {
                "location": 11,
                "is_targeted": False,
                "metadata_raw": None,
                "metadata_sealed": None,
                "traffic_metadata_raw": quest.get("traffic_metadata_raw"),
                "traffic_metadata_sealed": quest.get("traffic_metadata_sealed"),
            })
            if r.status_code in (200, 201, 204):
                log(f"Đã nhận quest: {Colors.BOLD}{name}{Colors.RESET}", "ok", self.api.username)
                send_webhook(
                    title="📌 Nhận Quest Mới Thành Công",
                    description=f"Tài khoản **{self.api.username}** vừa nhận nhiệm vụ **{name}**.",
                    color=0x3498DB,
                    fields=[
                        {"name": "Quest", "value": name, "inline": True},
                        {"name": "Quest ID", "value": str(qid), "inline": True},
                    ]
                )
                return True
            elif r.status_code == 429:
                wait = 10
                try:
                    wait = r.json().get("retry_after", 10)
                except Exception:
                    pass
                log(f"Discord giới hạn tốc độ nhận quest mới (Rate Limit 429). Tạm dừng nhận thêm quest ({wait:.0f}s).", "warn", self.api.username)
                return "RATE_LIMIT"
            elif r.status_code == 404:
                log(f"Quest [{name}] đã hết hạn hoặc không khả dụng trên tài khoản (HTTP 404).", "warn", self.api.username)
                return False
            else:
                log(f"Không thể nhận quest [{name}] (HTTP {r.status_code}): {r.text[:100]}", "warn", self.api.username)
        except Exception as e:
            log(f"Lỗi khi nhận quest [{name}]: {e}", "error", self.api.username)
        return False


    def claim_reward(self, quest: dict):
        """Tự động nhận thưởng và trích xuất gift code."""
        qid = quest["id"]
        name = get_quest_name(quest)
        try:
            # Thử endpoint hiện đại /claim-reward trước, sau đó fallback /claim
            r = self.api.post(f"/quests/{qid}/claim-reward", {"platform": 0, "location": 11})
            if r.status_code == 404:
                r = self.api.post(f"/quests/{qid}/claim", {"platform": 0})

            if r.status_code == 200:
                data = r.json()
                code = data.get("code")
                reward_text = code if code else "Đã nạp trực tiếp (Direct Entitlement / Orbs)"
                log(
                    f"🎉 ĐÃ NHẬN THƯỞNG CHO [{name}]! Mã code: {Colors.BOLD}{Colors.GREEN}{reward_text}{Colors.RESET}",
                    "reward",
                    self.api.username
                )

                # Lưu mã quà tặng vào file an toàn đa luồng
                with _rewards_lock:
                    with open(config.rewards_file, "a", encoding="utf-8") as f:
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"[{now_str}] Acc: {self.api.username} ({self.api.user_id}) | Quest: {name} | Code: {reward_text}\n")

                send_webhook(
                    title="🎁 Quest Hoàn Tất & Đã Nhận Quà!",
                    description=f"Tài khoản **{self.api.username}** đã hoàn thành nhiệm vụ và nhận quà thành công!",
                    color=0x00FF7F,
                    fields=[
                        {"name": "Tài khoản", "value": self.api.username, "inline": True},
                        {"name": "Nhiệm vụ", "value": name, "inline": True},
                        {"name": "Mã phần thưởng", "value": f"`{reward_text}`", "inline": False},
                    ]
                )
                if self.on_quest_complete:
                    try:
                        self.on_quest_complete(str(qid), name, reward_text, False)
                    except Exception:
                        pass
            elif "captcha" in r.text.lower():
                log(
                    f"🎉 Nhiệm vụ [{name}] đã hoàn tất 100%! Vui lòng mở Discord bấm 'Nhận Quà' (Discord yêu cầu xác minh Captcha cho tài khoản này).",
                    "reward",
                    self.api.username
                )
                send_webhook(
                    title="🎉 Quest Hoàn Tất 100%!",
                    description=f"Nhiệm vụ **{name}** đã hoàn thành 100% trên tài khoản **{self.api.username}**. Hãy mở Discord để bấm nhận quà.",
                    color=0xF1C40F,
                    fields=[
                        {"name": "Tài khoản", "value": self.api.username, "inline": True},
                        {"name": "Nhiệm vụ", "value": name, "inline": True},
                        {"name": "Trạng thái", "value": "Sẵn sàng nhận quà trong Discord", "inline": True},
                    ]
                )
                if self.on_quest_complete:
                    try:
                        self.on_quest_complete(str(qid), name, None, True)
                    except Exception:
                        pass
            else:
                log(f"Nhận thưởng [{name}] (HTTP {r.status_code}): {r.text[:100]}", "warn", self.api.username)
                if self.on_quest_complete:
                    try:
                        self.on_quest_complete(str(qid), name, None, False)
                    except Exception:
                        pass
        except Exception as e:
            log(f"Lỗi khi nhận thưởng [{name}]: {e}", "error", self.api.username)
            if self.on_quest_complete:
                try:
                    self.on_quest_complete(str(qid), name, None, False)
                except Exception:
                    pass


    def complete_video(self, quest: dict):
        """Mô phỏng xem video tăng tiến độ quest."""
        name = get_quest_name(quest)
        qid = quest["id"]
        seconds_needed = get_seconds_needed(quest)
        seconds_done = get_seconds_done(quest)
        enrolled_at_str = _get(get_user_status(quest), "enrolledAt", "enrolled_at")

        if enrolled_at_str:
            try:
                enrolled_ts = datetime.fromisoformat(enrolled_at_str.replace("Z", "+00:00")).timestamp()
            except Exception:
                enrolled_ts = time.time()
        else:
            enrolled_ts = time.time()

        log(f"Bắt đầu xem video: {Colors.BOLD}{name}{Colors.RESET} ({seconds_done:.0f}/{seconds_needed}s)", "info", self.api.username)
        if self.on_status:
            try:
                self.on_status(str(qid), name, "Bắt đầu xem video")
            except Exception:
                pass
        if self.on_progress:
            try:
                initial_pct = (seconds_done / seconds_needed) * 100 if seconds_needed > 0 else 0
                self.on_progress(str(qid), name, seconds_done, seconds_needed, initial_pct, "Đang xem video")
            except Exception:
                pass

        while seconds_done < seconds_needed:
            max_allowed = (time.time() - enrolled_ts) + 10
            timestamp = min(seconds_needed, seconds_done + 7)

            if max_allowed >= timestamp:
                try:
                    r = self.api.post(f"/quests/{qid}/video-progress", {
                        "timestamp": timestamp + random.uniform(0.1, 0.5)
                    })
                    if r.status_code == 200:
                        seconds_done = timestamp
                        pct = (seconds_done / seconds_needed) * 100 if seconds_needed > 0 else 100
                        log(f"[{name}] Tiến độ: {seconds_done:.0f}/{seconds_needed}s ({pct:.0f}%)", "prog", self.api.username)
                        if self.on_progress:
                            try:
                                self.on_progress(str(qid), name, seconds_done, seconds_needed, pct, "Đang xem video")
                            except Exception:
                                pass
                        if r.json().get("completed_at") or seconds_done >= seconds_needed:
                            break
                    elif r.status_code == 404:
                        log(f"[{name}] Nhiệm vụ không còn khả dụng trên Discord (HTTP 404). Hủy chạy.", "warn", self.api.username)
                        break
                    elif r.status_code == 429:
                        wait = r.json().get("retry_after", 5)
                        time.sleep(wait + 1)
                except Exception:
                    pass
            time.sleep(1)

        if seconds_done >= seconds_needed:
            log(f"✅ Hoàn thành video: {Colors.BOLD}{name}{Colors.RESET}", "ok", self.api.username)
            if self.on_progress:
                try:
                    self.on_progress(str(qid), name, seconds_needed, seconds_needed, 100.0, "Hoàn thành video")
                except Exception:
                    pass
            if config.auto_claim:
                self.claim_reward(quest)

    def complete_heartbeat(self, quest: dict):
        """Mô phỏng phát stream / chơi game gửi nhịp heartbeat."""
        name = get_quest_name(quest)
        qid = quest["id"]
        task_type = get_task_type(quest)
        seconds_needed = get_seconds_needed(quest)
        seconds_done = get_seconds_done(quest)
        pid = random.randint(1000, 30000)
        stream_key = f"call:0:{pid}" if task_type != "PLAY_ACTIVITY" else "call:0:1"

        remaining_mins = max(0, (seconds_needed - int(seconds_done)) // 60)
        log(f"Bắt đầu chạy: {Colors.BOLD}{name}{Colors.RESET} [{task_type}] còn ~{remaining_mins} phút", "info", self.api.username)
        if self.on_status:
            try:
                self.on_status(str(qid), name, f"Bắt đầu chạy [{task_type}]")
            except Exception:
                pass
        if self.on_progress:
            try:
                initial_pct = (seconds_done / seconds_needed) * 100 if seconds_needed > 0 else 0
                self.on_progress(str(qid), name, seconds_done, seconds_needed, initial_pct, "Đang stream/chơi game")
            except Exception:
                pass

        while seconds_done < seconds_needed:
            try:
                r = self.api.post(f"/quests/{qid}/heartbeat", {"stream_key": stream_key, "terminal": False})
                if r.status_code == 200:
                    data = r.json()
                    prog = data.get("progress", {})
                    if task_type in prog:
                        seconds_done = prog[task_type].get("value", seconds_done)
                    pct = (seconds_done / seconds_needed) * 100 if seconds_needed > 0 else 100
                    log(f"[{name}] Đang chạy: {seconds_done:.0f}/{seconds_needed}s ({pct:.0f}%)", "prog", self.api.username)
                    if self.on_progress:
                        try:
                            self.on_progress(str(qid), name, seconds_done, seconds_needed, pct, "Đang stream/chơi game")
                        except Exception:
                            pass
                    if data.get("completed_at") or seconds_done >= seconds_needed:
                        break
                elif r.status_code == 404:
                    log(f"[{name}] Nhiệm vụ không còn khả dụng trên Discord (HTTP 404). Dừng gửi heartbeat.", "warn", self.api.username)
                    break
                elif r.status_code == 429:
                    wait = r.json().get("retry_after", 10)
                    time.sleep(wait + 1)
                    continue
                else:
                    log(f"[{name}] Nhịp heartbeat trả về HTTP {r.status_code}", "warn", self.api.username)
            except Exception as e:
                log(f"[{name}] Lỗi gửi heartbeat: {e}", "warn", self.api.username)

            time.sleep(config.heartbeat_interval)

        # Gửi nhịp kết thúc terminal nếu đã hoàn tất
        if seconds_done >= seconds_needed:
            try:
                self.api.post(f"/quests/{qid}/heartbeat", {"stream_key": stream_key, "terminal": True})
            except Exception:
                pass

            log(f"✅ Hoàn thành: {Colors.BOLD}{name}{Colors.RESET}", "ok", self.api.username)
            if self.on_progress:
                try:
                    self.on_progress(str(qid), name, seconds_needed, seconds_needed, 100.0, "Hoàn thành")
                except Exception:
                    pass
            if config.auto_claim:
                self.claim_reward(quest)


    def complete_activity_achievement(self, quest: dict):
        """Hoàn thành quest dạng ACHIEVEMENT_IN_ACTIVITY qua Discord Says backend."""
        name = get_quest_name(quest)
        qid = quest["id"]
        app_id = get_app_id(quest)
        target = get_seconds_needed(quest) or 1

        if not app_id:
            log(f"[{name}] Không tìm thấy application ID của Activity.", "warn", self.api.username)
            return

        log(f"Bắt đầu xử lý Activity: {Colors.BOLD}{name}{Colors.RESET} (Mục tiêu: {target})", "info", self.api.username)
        if self.on_status:
            try:
                self.on_status(str(qid), name, "Đang xử lý Activity...")
            except Exception:
                pass

        try:
            # 1. Cấp quyền OAuth2 cho ứng dụng của quest
            auth_url = f"/oauth2/authorize?response_type=code&client_id={app_id}&scope=identify%20applications.commands%20applications.entitlements"
            auth_payload = {
                "permissions": "0",
                "authorize": True,
                "integration_type": 1,
                "location_context": {
                    "guild_id": "10000",
                    "channel_id": "10000",
                    "channel_type": 10000
                }
            }
            r_auth = self.api.post(auth_url, auth_payload)
            if r_auth.status_code != 200:
                log(f"[{name}] Cấp mã OAuth2 thất bại (HTTP {r_auth.status_code})", "warn", self.api.username)
                return

            loc = r_auth.json().get("location", "")
            parsed = urllib.parse.urlparse(loc)
            code = urllib.parse.parse_qs(parsed.query).get("code", [None])[0]
            if not code:
                log(f"[{name}] Không lấy được OAuth code từ URL chuyển hướng.", "warn", self.api.username)
                return

            # 2. Lấy proxy ticket
            r_ticket = self.api.post(f"/applications/{app_id}/proxy-tickets", {})
            if r_ticket.status_code != 200:
                log(f"[{name}] Lỗi khi tạo proxy ticket (HTTP {r_ticket.status_code})", "warn", self.api.username)
                return
            proxy_ticket = r_ticket.json().get("ticket", "")

            # 3. Xác thực với server Discord Says của Activity
            referrer = f"https://{app_id}.discordsays.com/?instance_id=example-cl-instance&platform=desktop&discord_proxy_ticket={urllib.parse.quote(proxy_ticket)}"
            headers = {
                "Content-Type": "application/json",
                "X-Auth-Token": "",
                "X-Discord-Quest-ID": str(qid),
                "Referer": referrer,
                "Origin": f"https://{app_id}.discordsays.com",
                "User-Agent": self.api.session.headers.get("User-Agent", "Mozilla/5.0")
            }
            ds_session = requests.Session()
            ds_session.trust_env = False

            ds_auth_url = f"https://{app_id}.discordsays.com/.proxy/acf/authorize"
            r_ds = ds_session.post(ds_auth_url, json={"code": code}, headers=headers, timeout=15)
            if r_ds.status_code != 200:
                log(f"[{name}] Xác thực trên Discord Says thất bại (HTTP {r_ds.status_code})", "warn", self.api.username)
                return

            ds_token = r_ds.json().get("token")
            if not ds_token:
                log(f"[{name}] Không tìm thấy session token từ Discord Says.", "warn", self.api.username)
                return

            # 4. Gửi tiến độ hoàn thành
            headers["X-Auth-Token"] = ds_token
            prog_url = f"https://{app_id}.discordsays.com/.proxy/acf/quest/progress"
            r_prog = ds_session.post(prog_url, json={"progress": target}, headers=headers, timeout=15)

            # 5. Thu hồi ngay OAuth token để đảm bảo an toàn tuyệt đối cho tài khoản
            try:
                r_tokens = self.api.get("/oauth2/tokens")
                if r_tokens.status_code == 200:
                    for tk in r_tokens.json():
                        if tk.get("application", {}).get("id") == app_id:
                            tk_id = tk.get("id")
                            self.api.session.delete(f"{config.api_base}/oauth2/tokens/{tk_id}")
            except Exception:
                pass

            if r_prog.status_code == 200:
                log(f"✅ Hoàn thành Activity: {Colors.BOLD}{name}{Colors.RESET}", "ok", self.api.username)
                if self.on_progress:
                    try:
                        self.on_progress(str(qid), name, target, target, 100.0, "Hoàn thành Activity")
                    except Exception:
                        pass
                if config.auto_claim:
                    self.claim_reward(quest)
            else:
                log(f"[{name}] Báo cáo tiến độ Activity thất bại (HTTP {r_prog.status_code}): {r_prog.text[:100]}", "warn", self.api.username)
        except Exception as e:
            log(f"[{name}] Lỗi khi chạy Activity: {e}", "error", self.api.username)

    def process_quest(self, quest: dict):
        """Điều phối việc hoàn thành quest theo từng loại nhiệm vụ."""
        qid = str(quest.get("id"))
        task_type = get_task_type(quest)

        with self._lock:
            if not task_type or qid in self.completed_ids:
                return
            self.completed_ids.add(qid)

        if task_type in ("WATCH_VIDEO", "WATCH_VIDEO_ON_MOBILE"):
            self.complete_video(quest)
        elif task_type == "ACHIEVEMENT_IN_ACTIVITY":
            self.complete_activity_achievement(quest)
        else:
            self.complete_heartbeat(quest)

    def run_cycle(self):
        """Chạy một chu kỳ quét và xử lý toàn bộ quest của tài khoản."""
        quests = self.fetch_quests()
        if not quests:
            return

        # 1. Tự động nhận quest mới nếu chưa enroll (chỉ chọn quest còn hạn và đã mở)
        if config.auto_accept:
            unaccepted = [
                q for q in quests
                if not is_enrolled(q)
                and not is_completed(q)
                and not is_expired(q)
                and has_started(q)
                and get_task_type(q)
            ]
            for q in unaccepted:
                res = self.enroll(q)
                if res == "RATE_LIMIT":
                    break
                time.sleep(3)
            if unaccepted:
                quests = self.fetch_quests()

        # 2. Kiểm tra nhận thưởng cho quest đã xong nhưng chưa claim
        if config.auto_claim:
            for q in quests:
                if is_completed(q) and not is_claimed(q):
                    self.claim_reward(q)

        # 3. Lọc danh sách quest cần cày tiến độ (bỏ qua quest đã hết hạn)
        actionable = [
            q for q in quests
            if is_enrolled(q)
            and not is_completed(q)
            and not is_expired(q)
            and get_task_type(q)
            and str(q.get("id")) not in self.completed_ids
        ]

        if actionable:
            log(f"Đang chạy SONG SONG {len(actionable)} quest...", "info", self.api.username)
            with ThreadPoolExecutor(max_workers=config.max_concurrent_quests) as pool:
                list(pool.map(self.process_quest, actionable))
        else:
            log("Không có quest nào cần cày tiến độ tại thời điểm này.", "info", self.api.username)
