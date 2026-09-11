import sys
import os
import re
import threading
from datetime import datetime

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

try:
    import colorama
    colorama.init()
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False



class Colors:
    RESET   = "\033[0m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    CYAN    = "\033[96m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    MAGENTA = "\033[95m"


_print_lock = threading.Lock()
_file_lock = threading.Lock()
_ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def strip_ansi(text: str) -> str:
    return _ansi_escape.sub('', text)


def log(msg: str, level: str = "info", prefix_tag: str = "", log_to_file: bool = True):
    now = datetime.now()
    ts = now.strftime("%H:%M:%S")
    badges = {
        "info":   f"{Colors.CYAN}[INFO]{Colors.RESET}",
        "ok":     f"{Colors.GREEN}[ OK ]{Colors.RESET}",
        "warn":   f"{Colors.YELLOW}[WARN]{Colors.RESET}",
        "error":  f"{Colors.RED}[ERR ]{Colors.RESET}",
        "prog":   f"{Colors.DIM}[PROG]{Colors.RESET}",
        "reward": f"{Colors.MAGENTA}[GIFT]{Colors.RESET}",
    }
    raw_badges = {
        "info":   "[INFO]",
        "ok":     "[ OK ]",
        "warn":   "[WARN]",
        "error":  "[ERR ]",
        "prog":   "[PROG]",
        "reward": "[GIFT]",
    }
    
    tag = f"[{prefix_tag}] " if prefix_tag else ""
    console_line = f"{Colors.DIM}{ts}{Colors.RESET} {badges.get(level, '[LOG]')} {tag}{msg}"
    
    with _print_lock:
        print(console_line)
        sys.stdout.flush()

    if log_to_file:
        try:
            date_str = now.strftime("%Y-%m-%d")
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, f"autoquest_{date_str}.log")
            
            clean_msg = strip_ansi(msg)
            raw_line = f"{now.strftime('%Y-%m-%d %H:%M:%S')} {raw_badges.get(level, '[LOG]')} {tag}{clean_msg}\n"
            
            with _file_lock:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(raw_line)
        except Exception:
            pass
