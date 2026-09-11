import requests
import json
import base64
import re
from typing import Optional
from src.config import config
from src.utils.logger import Colors, log

# Cache build number để không phải quét lại nhiều lần
_CACHED_BUILD_NUMBER: Optional[int] = None


def fetch_latest_build_number() -> int:
    """Quét và lấy số phiên bản Client Build Number mới nhất từ Discord."""
    global _CACHED_BUILD_NUMBER
    if _CACHED_BUILD_NUMBER is not None:
        return _CACHED_BUILD_NUMBER

    FALLBACK = 504649
    try:
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        session = requests.Session()
        session.trust_env = False
        r = session.get("https://discord.com/app", headers={"User-Agent": ua}, timeout=15)
        if r.status_code != 200:
            _CACHED_BUILD_NUMBER = FALLBACK
            return FALLBACK

        # Tìm các file JS bundle
        scripts = re.findall(r'src="(/assets/[^"]+?\.js)"', r.text)
        if not scripts:
            scripts = [f"/assets/{x}.js" for x in re.findall(r'/assets/([a-zA-Z0-9\.\_\-]+)\.js', r.text)]

        for script_url in reversed(scripts[-8:]):
            try:
                full_url = f"https://discord.com{script_url}" if script_url.startswith("/") else script_url
                ar = session.get(full_url, headers={"User-Agent": ua}, timeout=15)
                m = re.search(r'buildNumber["\s:]+["\s]*(\d{5,7})', ar.text)
                if m:
                    bn = int(m.group(1))
                    log(f"Discord Client Build Number phát hiện: {Colors.BOLD}{bn}{Colors.RESET}", "ok")
                    _CACHED_BUILD_NUMBER = bn
                    return bn
            except Exception:
                continue

        _CACHED_BUILD_NUMBER = FALLBACK
        return FALLBACK
    except Exception:
        _CACHED_BUILD_NUMBER = FALLBACK
        return FALLBACK


def make_super_properties(build_number: int) -> str:
    """Tạo payload X-Super-Properties giả lập Discord Desktop Client."""
    obj = {
        "os": "Windows",
        "browser": "Discord Client",
        "release_channel": "stable",
        "client_version": "1.0.9175",
        "os_version": "10.0.26100",
        "os_arch": "x64",
        "app_arch": "x64",
        "system_locale": "en-US",
        "browser_user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) discord/1.0.9175 Chrome/128.0.6613.186 Electron/32.2.7 Safari/537.36"
        ),
        "browser_version": "32.2.7",
        "client_build_number": build_number,
        "native_build_number": 59498,
        "client_event_source": None,
    }
    return base64.b64encode(json.dumps(obj).encode()).decode()


class DiscordAPI:
    def __init__(self, token: str, build_number: int):
        self.token = token
        self.username = "Unknown"
        self.user_id = ""
        self.build_number = build_number
        self.session = requests.Session()
        self.session.trust_env = False

        sp = make_super_properties(build_number)
        self.session.headers.update({
            "Authorization": token,
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) discord/1.0.9175 Chrome/128.0.6613.186 Electron/32.2.7 Safari/537.36"
            ),
            "X-Super-Properties": sp,
            "Origin": "https://discord.com",
            "Referer": "https://discord.com/channels/@me",
        })

    def get(self, path: str, **kwargs) -> requests.Response:
        url = f"{config.api_base}{path}"
        return self.session.get(url, **kwargs)

    def post(self, path: str, payload: Optional[dict] = None, **kwargs) -> requests.Response:
        url = f"{config.api_base}{path}"
        return self.session.post(url, json=payload, **kwargs)

    def validate(self) -> bool:
        """Kiểm tra tính hợp lệ của token và lấy thông tin tài khoản."""
        try:
            r = self.get("/users/@me", timeout=15)
            if r.status_code == 200:
                data = r.json()
                self.username = data.get("global_name") or data.get("username", "Unknown")
                self.user_id = data.get("id", "")
                log(f"Đăng nhập thành công: {Colors.BOLD}{self.username}{Colors.RESET} (ID: {self.user_id})", "ok")
                return True
            else:
                log(f"Xác thực thất bại (HTTP {r.status_code}): Token không hợp lệ hoặc đã bị đổi.", "error")
                return False
        except Exception as e:
            log(f"Lỗi khi xác thực token: {e}", "error")
            return False
