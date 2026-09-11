import os
import json
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    api_base: str = "https://discord.com/api/v9"
    poll_interval: int = 60
    heartbeat_interval: int = 20
    auto_accept: bool = True
    auto_claim: bool = True
    max_concurrent_quests: int = 5
    discord_webhook_url: str = ""
    log_to_file: bool = True
    rewards_file: str = "data/rewards.txt"
    bot_token: str = ""
    supported_tasks: List[str] = field(default_factory=lambda: [
        "WATCH_VIDEO",
        "PLAY_ON_DESKTOP",
        "STREAM_ON_DESKTOP",
        "PLAY_ACTIVITY",
        "WATCH_VIDEO_ON_MOBILE",
        "ACHIEVEMENT_IN_ACTIVITY",
    ])

    @classmethod
    def load(cls, config_path: str = "config.json") -> "AppConfig":
        data = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[CẢNH BÁO] Không thể đọc {config_path}: {e}. Sử dụng cấu hình mặc định.")

        # Lấy từ config.json hoặc biến môi trường hoặc giá trị mặc định
        api_base = os.getenv("API_BASE", data.get("api_base", "https://discord.com/api/v9"))
        poll_interval = int(os.getenv("POLL_INTERVAL", data.get("poll_interval", 60)))
        heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", data.get("heartbeat_interval", 20)))
        
        auto_accept_val = os.getenv("AUTO_ACCEPT", data.get("auto_accept", True))
        if isinstance(auto_accept_val, str):
            auto_accept = auto_accept_val.strip().lower() in ("1", "true", "yes")
        else:
            auto_accept = bool(auto_accept_val)

        auto_claim_val = os.getenv("AUTO_CLAIM", data.get("auto_claim", True))
        if isinstance(auto_claim_val, str):
            auto_claim = auto_claim_val.strip().lower() in ("1", "true", "yes")
        else:
            auto_claim = bool(auto_claim_val)

        max_concurrent = int(os.getenv("MAX_CONCURRENT_QUESTS", data.get("max_concurrent_quests", 5)))
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", data.get("discord_webhook_url", "")).strip()
        bot_token = (os.getenv("DISCORD_BOT_TOKEN") or os.getenv("BOT_TOKEN") or data.get("bot_token", "")).strip()

        log_to_file_val = os.getenv("LOG_TO_FILE", data.get("log_to_file", True))
        if isinstance(log_to_file_val, str):
            log_to_file = log_to_file_val.strip().lower() in ("1", "true", "yes")
        else:
            log_to_file = bool(log_to_file_val)

        rewards_file = os.getenv("REWARDS_FILE", data.get("rewards_file", "data/rewards.txt"))

        # Đảm bảo thư mục lưu data & logs tồn tại
        rewards_dir = os.path.dirname(rewards_file)
        if rewards_dir and not os.path.exists(rewards_dir):
            os.makedirs(rewards_dir, exist_ok=True)

        if log_to_file and not os.path.exists("logs"):
            os.makedirs("logs", exist_ok=True)

        return cls(
            api_base=api_base,
            poll_interval=poll_interval,
            heartbeat_interval=heartbeat_interval,
            auto_accept=auto_accept,
            auto_claim=auto_claim,
            max_concurrent_quests=max_concurrent,
            discord_webhook_url=webhook_url,
            log_to_file=log_to_file,
            rewards_file=rewards_file,
            bot_token=bot_token,
        )


# Global singleton config
config: AppConfig = AppConfig.load()
