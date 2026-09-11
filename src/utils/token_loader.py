import os
import sys
from typing import List
from src.utils.logger import Colors, log


def clean_token(token: str) -> str:
    """Loại bỏ khoảng trắng và dấu ngoặc kép/đơn bao quanh token nếu có."""
    t = token.strip()
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()
    return t


def get_tokens(tokens_file: str = "tokens.txt") -> List[str]:
    """
    Nạp danh sách Discord Token theo thứ tự ưu tiên:
    1. Tham số dòng lệnh (sys.argv)
    2. File tokens.txt
    3. File .token
    4. Biến môi trường DISCORD_TOKEN
    5. Nhập trực tiếp từ bàn phím (nếu chưa có bất kỳ nguồn nào)
    """
    tokens = []

    # 1. Kiểm tra tham số dòng lệnh (bỏ qua các flag bắt đầu bằng '-')
    cli_tokens = [clean_token(arg) for arg in sys.argv[1:] if not arg.startswith("-")]
    if cli_tokens:
        tokens.extend(cli_tokens)

    # 2. Kiểm tra file tokens.txt
    if not tokens and os.path.exists(tokens_file):
        try:
            with open(tokens_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        cleaned = clean_token(line)
                        if cleaned:
                            tokens.append(cleaned)
        except Exception as e:
            log(f"Lỗi khi đọc file {tokens_file}: {e}", "warn")

    # 3. Kiểm tra file .token
    if not tokens and os.path.exists(".token"):
        try:
            with open(".token", "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    tokens.append(clean_token(content))
        except Exception:
            pass

    # 4. Kiểm tra biến môi trường DISCORD_TOKEN
    if not tokens:
        env_token = os.getenv("DISCORD_TOKEN", "").strip()
        if env_token:
            tokens.append(clean_token(env_token))

    # 5. Nếu vẫn chưa có token nào, hỏi người dùng nhập qua Console
    if not tokens:
        try:
            print()
            input_token = input(f"{Colors.BOLD}{Colors.CYAN}Nhập Discord Token của bạn: {Colors.RESET}").strip()
            if input_token:
                cleaned = clean_token(input_token)
                tokens.append(cleaned)
                
                # Tự động lưu token vào tokens.txt cho các lần chạy sau
                try:
                    with open(tokens_file, "a", encoding="utf-8") as f:
                        f.write(f"\n{cleaned}\n")
                    log(f"Đã lưu token vào {tokens_file} để tái sử dụng.", "ok")
                except Exception:
                    pass
        except (KeyboardInterrupt, EOFError):
            print()
            return []

    # Loại bỏ token trùng lặp nhưng giữ nguyên thứ tự xuất hiện
    unique_tokens = list(dict.fromkeys(tokens))
    return unique_tokens
