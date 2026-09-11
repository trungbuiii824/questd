import asyncio
import time
import threading
from typing import Dict, Any, Optional, List
import discord

from src.discord.api import DiscordAPI
from src.worker.quest_worker import QuestWorker
from src.discord.models import (
    get_quest_name,
    get_task_type,
    get_seconds_needed,
    get_seconds_done,
    is_completed,
    is_claimed,
    is_expired,
    has_started,
)
from src.utils.logger import log


def make_progress_bar(pct: float, length: int = 10) -> str:
    """Tạo chuỗi thanh tiến độ Unicode dạng [████████░░]."""
    pct = max(0.0, min(100.0, pct))
    filled = int(round(length * (pct / 100.0)))
    empty = length - filled
    return "█" * filled + "░" * empty


class QuestSession:
    """Quản lý một phiên cày quest độc lập cho từng người dùng qua Discord Bot."""

    def __init__(self, interaction: discord.Interaction, api: DiscordAPI, message: discord.WebhookMessage):
        self.interaction = interaction
        self.message = message
        self.user = interaction.user
        self.api = api
        self.start_time = time.time()
        self.is_running = True
        self.lock = threading.Lock()

        # Quản lý danh sách quest khả dụng: qid -> dict
        self.quests_state: Dict[str, Dict[str, Any]] = {}
        self.claimed_rewards: List[Dict[str, Any]] = []
        self.status_message: str = "Đang khởi tạo danh sách nhiệm vụ..."

        # Khởi tạo QuestWorker với callback
        self.worker = QuestWorker(
            api=self.api,
            on_progress=self._on_progress,
            on_quest_complete=self._on_quest_complete,
            on_status=self._on_status,
        )

    def _on_status(self, qid: str, name: str, status_text: str):
        with self.lock:
            if qid not in self.quests_state:
                self.quests_state[qid] = {
                    "name": name,
                    "current": 0,
                    "total": 1,
                    "percent": 0.0,
                    "status": status_text,
                    "code": None,
                    "captcha": False,
                    "completed": False,
                }
            else:
                self.quests_state[qid]["status"] = status_text

    def _on_progress(self, qid: str, name: str, current: float, total: float, pct: float, status_text: str):
        with self.lock:
            if qid not in self.quests_state:
                self.quests_state[qid] = {
                    "name": name,
                    "current": current,
                    "total": total,
                    "percent": pct,
                    "status": status_text,
                    "code": None,
                    "captcha": False,
                    "completed": pct >= 100.0,
                }
            else:
                self.quests_state[qid]["current"] = current
                self.quests_state[qid]["total"] = total
                self.quests_state[qid]["percent"] = pct
                self.quests_state[qid]["status"] = status_text
                if pct >= 100.0:
                    self.quests_state[qid]["completed"] = True

    def _on_quest_complete(self, qid: str, name: str, reward_code: Optional[str], requires_captcha: bool):
        with self.lock:
            if qid in self.quests_state:
                self.quests_state[qid]["completed"] = True
                self.quests_state[qid]["code"] = reward_code
                self.quests_state[qid]["captcha"] = requires_captcha
                self.quests_state[qid]["percent"] = 100.0
            else:
                self.quests_state[qid] = {
                    "name": name,
                    "current": 1,
                    "total": 1,
                    "percent": 100.0,
                    "status": "Hoàn thành",
                    "code": reward_code,
                    "captcha": requires_captcha,
                    "completed": True,
                }

            self.claimed_rewards.append({
                "qid": qid,
                "name": name,
                "code": reward_code,
                "captcha": requires_captcha,
            })

    def build_running_embed(self) -> discord.Embed:
        """Xây dựng Embed tiến độ thời gian thực (Giới hạn field tránh quá tải Discord 25-field limit)."""
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)

        with self.lock:
            items = list(self.quests_state.items())

        active_quests = [item for item in items if not item[1].get("completed", False)]
        completed_quests = [item for item in items if item[1].get("completed", False)]

        embed = discord.Embed(
            title="⚡ Discord Quest Auto-Completer v4.0",
            description=(
                f"👤 Tài khoản Discord: **{self.api.username}** (`{self.api.user_id}`)\n"
                f"⏱️ Thời gian đã chạy: **{mins:02d}:{secs:02d}**\n"
                f"📊 Đang cày: **{len(active_quests)} quest** | Đã xong: **{len(completed_quests)} quest**\n"
                f"📌 Trạng thái: {self.status_message}"
            ),
            color=0x5865F2,  # Blurple
        )

        if not items:
            embed.add_field(
                name="🔍 Đang tìm kiếm nhiệm vụ...",
                value="Vui lòng đợi vài giây để bot quét các quest khả dụng trên tài khoản.",
                inline=False
            )
        else:
            # 1. Hiển thị các nhiệm vụ đang chạy (tối đa 8 quest để giao diện gọn gàng)
            for qid, data in active_quests[:8]:
                pct = data.get("percent", 0.0)
                bar = make_progress_bar(pct, length=10)
                status = data.get("status", "Đang xử lý")
                name = data.get("name", f"Quest #{qid}")
                cur = data.get("current", 0)
                tot = data.get("total", 0)
                progress_info = f" ({cur:.0f}/{tot:.0f}s)" if tot > 0 else ""
                val = f"`[{bar}] {pct:.0f}%` • {status}{progress_info}"
                embed.add_field(name=f"🎮 {name}", value=val, inline=False)

            if len(active_quests) > 8:
                embed.add_field(
                    name="⏳ Nhiệm vụ chờ",
                    value=f"...và còn {len(active_quests) - 8} nhiệm vụ khác đang chờ trong hàng đợi.",
                    inline=False
                )

            # 2. Tóm tắt các nhiệm vụ đã hoàn thành (gọn gàng, không tràn 25 fields)
            if completed_quests:
                done_names = []
                for _, d in completed_quests:
                    n = d.get("name", "Quest")
                    if d.get("code"):
                        done_names.append(f"• **{n}** (🎁 Có Code)")
                    elif d.get("captcha"):
                        done_names.append(f"• **{n}** (⚠️ Cần Captcha)")
                    else:
                        done_names.append(f"• **{n}** (✅)")

                chunk = "\n".join(done_names[:6])
                if len(done_names) > 6:
                    chunk += f"\n*...và {len(done_names) - 6} quest khác.*"

                embed.add_field(
                    name=f"✅ Đã Hoàn Thành ({len(completed_quests)} quest)",
                    value=chunk,
                    inline=False
                )

        embed.set_footer(
            text="🔒 Tin nhắn chỉ hiển thị với bạn (Ephemeral). Tiến độ tự cập nhật mỗi 3s.",
            icon_url="https://assets-global.website-files.com/6257adef93867e50d84d30e2/636e0a6a49cf127bf92de1e2_icon_clyde_blurple_RGB.png"
        )
        return embed

    def build_finished_embed(self) -> discord.Embed:
        """Xây dựng Embed tổng kết khi đã cày xong toàn bộ nhiệm vụ."""
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)

        with self.lock:
            items = list(self.quests_state.items())

        completed_quests = [item for item in items if item[1].get("completed", False)]

        embed = discord.Embed(
            title="🎉 Hoàn Tất Cày Discord Quests!",
            description=(
                f"👤 Tài khoản Discord: **{self.api.username}** (`{self.api.user_id}`)\n"
                f"⏱️ Tổng thời gian: **{mins:02d}:{secs:02d}**\n"
                f"🎯 Đã xử lý xong toàn bộ nhiệm vụ khả dụng!"
            ),
            color=0x57F287,  # Green
        )

        if not items:
            embed.add_field(
                name="ℹ️ Thông Báo",
                value="Tài khoản này hiện tại không có quest nào cần cày tiến độ hoặc tất cả đã hoàn thành trước đó.",
                inline=False
            )
        else:
            # Liệt kê tóm tắt quà tặng
            rewards_list = []
            captcha_list = []
            other_list = []

            for qid, data in items:
                name = data.get("name", f"Quest #{qid}")
                code = data.get("code")
                captcha = data.get("captcha", False)

                if code:
                    rewards_list.append(f"• **{name}**: `{code}`")
                elif captcha:
                    captcha_list.append(f"• **{name}** *(Mở Discord bấm 'Nhận Quà' để giải Captcha)*")
                else:
                    other_list.append(f"• **{name}** *(Đã hoàn thành)*")

            if rewards_list:
                embed.add_field(
                    name="🎁 Mã Quà Tặng Nhận Được",
                    value="\n".join(rewards_list[:8]),
                    inline=False
                )
            if captcha_list:
                embed.add_field(
                    name="⚠️ Cần Xác Minh Captcha Trong App",
                    value="\n".join(captcha_list[:5]),
                    inline=False
                )
            if other_list:
                embed.add_field(
                    name="✅ Nhiệm Vụ Hoàn Tất Khác",
                    value="\n".join(other_list[:5]),
                    inline=False
                )

        embed.set_footer(
            text="✨ Mã phần thưởng đã được gửi bảo mật vào tin nhắn riêng (DM) của bạn!",
        )
        return embed

    async def _updater_loop(self):
        """Loop định kỳ cập nhật tin nhắn tương tác trên Discord mỗi 3 giây."""
        last_edit_time = 0
        while self.is_running:
            await asyncio.sleep(3)
            if not self.is_running:
                break
            try:
                now = time.time()
                if now - last_edit_time >= 2.5:
                    embed = self.build_running_embed()
                    await self.message.edit(embed=embed)
                    last_edit_time = now
            except discord.NotFound:
                # Người dùng đã bấm tắt / đóng tin nhắn ephemeral
                break
            except Exception as e:
                # Tránh lỗi âm thầm, log rõ ràng
                log(f"Cập nhật Embed ({self.api.username}): {e}", "warn")

    async def run(self):
        """Khởi động tiến trình cày quest và đồng bộ với Discord Embed."""
        updater_task = asyncio.create_task(self._updater_loop())

        try:
            self.status_message = "Đang quét danh sách quest từ Discord..."
            # Chạy logic worker trong Thread riêng để không block asyncio loop
            await asyncio.to_thread(self._execute_worker_cycle)
        except Exception as e:
            log(f"Lỗi phiên bot quest: {e}", "error")
            self.status_message = f"Gặp lỗi khi xử lý: {e}"
        finally:
            self.is_running = False
            updater_task.cancel()
            try:
                await updater_task
            except asyncio.CancelledError:
                pass

            # Cập nhật kết quả cuối cùng lên tin nhắn tương tác
            final_embed = self.build_finished_embed()
            try:
                await self.message.edit(embed=final_embed)
            except Exception as e:
                log(f"Không thể cập nhật Embed cuối ({self.api.username}): {e}", "warn")

            # Gửi mã quà vào tin nhắn riêng (DM) cho người dùng
            await self._send_dm_summary()

    def _execute_worker_cycle(self):
        """Thực thi chu trình cày quest qua QuestWorker."""
        quests = self.worker.fetch_quests()
        if not quests:
            self.status_message = "Không tìm thấy quest nào trên tài khoản."
            return

        # Chỉ lọc những quest còn hạn và có loại task hợp lệ để không bị tràn Discord Embed
        relevant_quests = [
            q for q in quests
            if not is_expired(q) and get_task_type(q) and has_started(q)
        ]

        # Nạp trạng thái ban đầu của các quest hợp lệ
        for q in relevant_quests:
            qid = str(q.get("id"))
            name = get_quest_name(q)
            sec_needed = get_seconds_needed(q)
            sec_done = get_seconds_done(q)
            pct = (sec_done / sec_needed) * 100 if sec_needed > 0 else 0
            if is_completed(q):
                pct = 100.0

            with self.lock:
                self.quests_state[qid] = {
                    "name": name,
                    "current": sec_done,
                    "total": sec_needed,
                    "percent": pct,
                    "status": "Đã hoàn thành" if is_completed(q) else "Đang chuẩn bị",
                    "code": None,
                    "captcha": False,
                    "completed": is_completed(q),
                }

        self.status_message = "Đang tiến hành cày nhiệm vụ..."
        self.worker.run_cycle()
        self.status_message = "Hoàn tất toàn bộ chu kỳ!"

    async def _send_dm_summary(self):
        """Gửi danh sách mã quà tặng (Gift Codes) bảo mật vào DM của user."""
        try:
            dm_embed = discord.Embed(
                title="🎁 Tổng Kết Phần Thưởng Discord Quest",
                description=(
                    f"Chào **{self.user.name}**,\n"
                    f"Nhiệm vụ Discord Quests cho tài khoản **{self.api.username}** đã được hoàn tất!\n"
                    f"Dưới đây là mã quà tặng (Gift Code) của bạn:"
                ),
                color=0x00FF7F,
            )

            has_rewards = False
            with self.lock:
                for qid, data in self.quests_state.items():
                    name = data.get("name")
                    code = data.get("code")
                    captcha = data.get("captcha", False)
                    if code:
                        has_rewards = True
                        dm_embed.add_field(
                            name=f"🎮 {name}",
                            value=f"```\n{code}\n```*(Bấm đúp chuột vào ô trên để sao chép nhanh)*",
                            inline=False
                        )
                    elif captcha:
                        dm_embed.add_field(
                            name=f"🎮 {name}",
                            value="⚠️ Nhiệm vụ đã 100%, hãy mở app Discord và bấm **Nhận Quà** để giải Captcha.",
                            inline=False
                        )

            if not has_rewards and not any(d.get("captcha") for d in self.quests_state.values()):
                dm_embed.add_field(
                    name="ℹ️ Thông Báo",
                    value="Không có mã Gift Code mới nào (Có thể phần thưởng đã được nạp trực tiếp vào tài khoản Discord hoặc đã nhận trước đó).",
                    inline=False
                )

            dm_embed.set_footer(text="AutoQuest Bot • Chúc bạn chơi game vui vẻ!")
            await self.user.send(embed=dm_embed)
        except discord.Forbidden:
            log(f"Không thể gửi DM tới {self.user} do người dùng chặn DM.", "warn")
        except Exception as e:
            log(f"Lỗi khi gửi DM: {e}", "warn")
