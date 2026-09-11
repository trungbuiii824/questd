#!/usr/bin/env python3
"""
Discord Quest Auto-Completer v4.0 PRO
- Chạy song song đa luồng (Multi-threaded Quests)
- Tự động nhận quà & Lưu mã Redeem Code (Auto Claim Rewards)
- Gửi thông báo Discord Webhook dạng Rich Embed
- Hỗ trợ chạy nhiều Token (Multi-Token / tokens.txt)
"""

import sys
import time
import signal
import argparse
from typing import List

# Đảm bảo Windows Terminal / Console hỗ trợ hiển thị tiếng Việt UTF-8
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


from src.config import config, AppConfig
from src.discord.api import DiscordAPI, fetch_latest_build_number
from src.worker.quest_worker import QuestWorker
from src.utils.logger import Colors, log
from src.utils.token_loader import get_tokens
from src.utils.notifier import test_webhook


_is_running = True


def handle_exit(sig, frame):
    global _is_running
    print()
    log("Nhận tín hiệu dừng, đang hoàn tất các luồng và thoát an toàn...", "warn")
    _is_running = False
    sys.exit(0)


def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║             DISCORD QUEST AUTO-COMPLETER v4.0 PRO            ║
║  * Đa luồng song song  * Tự động nhận quà  * Webhook Discord ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
    """
    print(banner)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Discord Quest Auto-Completer v4.0 PRO - Tự động cày nhiệm vụ Discord",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--test-webhook",
        action="store_true",
        help="Kiểm tra kết nối và gửi tin nhắn thử nghiệm tới Discord Webhook"
    )
    parser.add_argument(
        "--single-run",
        action="store_true",
        help="Chỉ quét và hoàn thành nhiệm vụ 1 lần rồi thoát (không lặp vô tận)"
    )
    parser.add_argument(
        "--config",
        dest="config_path",
        default="config.json",
        help="Đường dẫn tới file cấu hình (mặc định: config.json)"
    )
    parser.add_argument(
        "--tokens",
        dest="tokens_path",
        default="tokens.txt",
        help="Đường dẫn tới file token (mặc định: tokens.txt)"
    )
    parser.add_argument(
        "token_args",
        nargs="*",
        help="Một hoặc nhiều Discord Token truyền trực tiếp qua dòng lệnh"
    )
    return parser.parse_args()


def main():
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    args = parse_args()
    print_banner()

    # Nạp lại cấu hình nếu người dùng chỉ định đường dẫn khác
    if args.config_path != "config.json":
        global config
        config = AppConfig.load(args.config_path)

    # Chế độ kiểm tra Webhook
    if args.test_webhook:
        test_webhook()
        return

    # Nạp danh sách tokens
    tokens = get_tokens(args.tokens_path)
    if not tokens:
        log("Không tìm thấy token nào để chạy! Vui lòng thêm token vào tokens.txt", "error")
        return

    log(f"Đã phát hiện {len(tokens)} token tài khoản.", "info")

    # Lấy build number của Discord client
    build_number = fetch_latest_build_number()
    workers: List[QuestWorker] = []

    # Khởi tạo và xác thực từng tài khoản
    for idx, token in enumerate(tokens, start=1):
        log(f"Đang kiểm tra tài khoản #{idx}...", "info")
        api = DiscordAPI(token, build_number)
        if api.validate():
            workers.append(QuestWorker(api))
        else:
            log(f"Bỏ qua token #{idx} do không hợp lệ.", "warn")

    if not workers:
        log("Không có tài khoản nào xác thực thành công. Dừng chương trình.", "error")
        return

    log(f"Sẵn sàng hoạt động cho {len(workers)} tài khoản hợp lệ!", "ok")
    print(f"{Colors.DIM}--------------------------------------------------------------{Colors.RESET}")

    cycle_count = 1
    while _is_running:
        log(f"=== Bắt đầu chu kỳ quét #{cycle_count} ===", "info")

        for worker in workers:
            if not _is_running:
                break
            log(f"Bắt đầu xử lý cho tài khoản: {Colors.BOLD}{worker.api.username}{Colors.RESET}", "info")
            worker.run_cycle()

        if args.single_run:
            log("Chế độ --single-run hoàn tất. Đã thoát chương trình.", "ok")
            break

        log(f"Nghỉ {config.poll_interval} giây trước chu kỳ quét tiếp theo...\n", "info")
        
        # Sleep chia nhỏ để phản hồi ngay lập tức khi người dùng bấm Ctrl + C
        for _ in range(config.poll_interval):
            if not _is_running:
                break
            time.sleep(1)

        cycle_count += 1


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        log("Đã dừng chương trình.", "warn")
