#!/usr/bin/env python3
"""
Discord Quest Service Bot - Desktop GUI Control Panel v4.0 PRO
- Giao diện trực quan (GUI) điều khiển bật/tắt Discord Bot 1-click
- Cấu hình Bot Token & lưu tự động vào config.json
- Theo dõi log thời gian thực với màu sắc trực quan
- Mở link mời bot vào server với 1 nút bấm
"""

import sys
import os
import json
import re
import base64
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Đảm bảo đường dẫn làm việc luôn là thư mục chứa script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILE = "config.json"


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_bot_id_from_token(token: str) -> str:
    """Giải mã phần đầu của Discord Token để lấy Application/Bot ID."""
    try:
        parts = token.strip().split(".")
        if parts:
            part1 = parts[0]
            # Padding nếu cần
            padding = len(part1) % 4
            if padding:
                part1 += "=" * (4 - padding)
            decoded = base64.b64decode(part1).decode("utf-8")
            if decoded.isdigit():
                return decoded
    except Exception:
        pass
    return ""


class AutoQuestGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AutoQuest Bot Controller v4.0 PRO")
        self.root.geometry("860x650")
        self.root.minsize(780, 560)

        # Màu sắc phong cách Discord Dark Theme
        self.BG_MAIN = "#1e1f22"
        self.BG_CARD = "#2b2d31"
        self.BG_INPUT = "#383a40"
        self.BG_CONSOLE = "#111214"
        self.TEXT_MAIN = "#f2f3f5"
        self.TEXT_MUTED = "#949ba4"
        self.ACCENT_BLURPLE = "#5865f2"
        self.ACCENT_GREEN = "#23a55a"
        self.ACCENT_RED = "#da373c"
        self.ACCENT_YELLOW = "#f0b232"

        self.root.configure(bg=self.BG_MAIN)

        self.process: subprocess.Popen = None
        self.is_running = False
        self.bot_name = "Chưa kết nối"
        self.bot_id = ""

        self._init_styles()
        self._build_ui()
        self._load_initial_data()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _init_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Cấu hình phong cách các widget
        style.configure(".", background=self.BG_MAIN, foreground=self.TEXT_MAIN, font=("Segoe UI", 10))
        style.configure("Card.TFrame", background=self.BG_CARD, relief="flat")
        style.configure("Header.TLabel", background=self.BG_MAIN, foreground=self.TEXT_MAIN, font=("Segoe UI", 14, "bold"))
        style.configure("SubHeader.TLabel", background=self.BG_MAIN, foreground=self.TEXT_MUTED, font=("Segoe UI", 9))
        style.configure("CardLabel.TLabel", background=self.BG_CARD, foreground=self.TEXT_MAIN, font=("Segoe UI", 10, "bold"))
        style.configure("CardSub.TLabel", background=self.BG_CARD, foreground=self.TEXT_MUTED, font=("Segoe UI", 9))

    def _build_ui(self):
        # 1. HEADER BANNER
        header_frame = tk.Frame(self.root, bg=self.BG_MAIN)
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        title_lbl = tk.Label(
            header_frame,
            text="⚡ BẢNG ĐIỀU KHIỂN AUTO QUEST",
            bg=self.BG_MAIN,
            fg=self.TEXT_MAIN,
            font=("Segoe UI", 13, "bold")
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            header_frame,
            text="Tự động làm nhiệm vụ nhận quà Discord nhanh chóng & an toàn",
            bg=self.BG_MAIN,
            fg=self.TEXT_MUTED,
            font=("Segoe UI", 9)
        )
        sub_lbl.pack(anchor="w")

        # 2. STATUS BAR CARD
        status_card = tk.Frame(self.root, bg=self.BG_CARD, padx=15, pady=12)
        status_card.pack(fill="x", padx=20, pady=5)

        # Trạng thái bên trái
        status_left = tk.Frame(status_card, bg=self.BG_CARD)
        status_left.pack(side="left", fill="y")

        self.status_dot = tk.Label(status_left, text="●", fg=self.ACCENT_RED, bg=self.BG_CARD, font=("Segoe UI", 16))
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_text = tk.Label(
            status_left,
            text="BOT ĐANG TẮT",
            fg=self.ACCENT_RED,
            bg=self.BG_CARD,
            font=("Segoe UI", 11, "bold")
        )
        self.status_text.pack(side="left")

        # Thông tin Bot bên phải
        self.bot_info_lbl = tk.Label(
            status_card,
            text="Tài khoản: Chưa đăng nhập",
            fg=self.TEXT_MUTED,
            bg=self.BG_CARD,
            font=("Segoe UI", 10)
        )
        self.bot_info_lbl.pack(side="right")

        # 3. CẤU HÌNH TOKEN
        cfg_card = tk.Frame(self.root, bg=self.BG_CARD, padx=15, pady=12)
        cfg_card.pack(fill="x", padx=20, pady=5)

        tk.Label(
            cfg_card,
            text="🔑 Discord Bot Token:",
            bg=self.BG_CARD,
            fg=self.TEXT_MAIN,
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))

        token_row = tk.Frame(cfg_card, bg=self.BG_CARD)
        token_row.grid(row=1, column=0, columnspan=3, sticky="ew")
        cfg_card.columnconfigure(0, weight=1)
        token_row.columnconfigure(0, weight=1)

        self.token_var = tk.StringVar()
        self.token_entry = tk.Entry(
            token_row,
            textvariable=self.token_var,
            show="*",
            bg=self.BG_INPUT,
            fg=self.TEXT_MAIN,
            insertbackground="white",
            relief="flat",
            font=("Consolas", 10),
            bd=5
        )
        self.token_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.show_token_btn = tk.Button(
            token_row,
            text="👁 Hiện",
            bg=self.BG_INPUT,
            fg=self.TEXT_MAIN,
            relief="flat",
            font=("Segoe UI", 9),
            padx=10,
            command=self.toggle_token_visibility
        )
        self.show_token_btn.grid(row=0, column=1, padx=(0, 8))

        self.save_btn = tk.Button(
            token_row,
            text="💾 Lưu Token",
            bg=self.ACCENT_BLURPLE,
            fg="white",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            command=self.save_token_action
        )
        self.save_btn.grid(row=0, column=2)

        # 4. NÚT ĐIỀU KHIỂN CHÍNH
        btn_frame = tk.Frame(self.root, bg=self.BG_MAIN)
        btn_frame.pack(fill="x", padx=20, pady=10)

        self.start_btn = tk.Button(
            btn_frame,
            text="▶ KHỞI ĐỘNG BOT",
            bg=self.ACCENT_GREEN,
            fg="white",
            relief="flat",
            font=("Segoe UI", 11, "bold"),
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.start_bot
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹ DỪNG BOT",
            bg=self.BG_INPUT,
            fg=self.TEXT_MUTED,
            relief="flat",
            font=("Segoe UI", 11, "bold"),
            padx=20,
            pady=8,
            state="disabled",
            cursor="hand2",
            command=self.stop_bot
        )
        self.stop_btn.pack(side="left", padx=(0, 10))

        self.invite_btn = tk.Button(
            btn_frame,
            text="🌐 Mời Bot Vào Server",
            bg=self.BG_INPUT,
            fg=self.TEXT_MAIN,
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.open_invite_link
        )
        self.invite_btn.pack(side="left", padx=(0, 10))

        self.rewards_btn = tk.Button(
            btn_frame,
            text="🎁 Mã Quà",
            bg=self.BG_INPUT,
            fg=self.TEXT_MAIN,
            relief="flat",
            font=("Segoe UI", 9),
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.open_rewards_file
        )
        self.rewards_btn.pack(side="right")

        self.folder_btn = tk.Button(
            btn_frame,
            text="📂 Thư Mục",
            bg=self.BG_INPUT,
            fg=self.TEXT_MAIN,
            relief="flat",
            font=("Segoe UI", 9),
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.open_working_folder
        )
        self.folder_btn.pack(side="right", padx=(0, 8))

        # 5. KHUNG TERMINAL LOGS
        log_header = tk.Frame(self.root, bg=self.BG_MAIN)
        log_header.pack(fill="x", padx=20, pady=(5, 2))

        tk.Label(
            log_header,
            text="📜 Nhật Ký Hoạt Động (Live Terminal Logs):",
            bg=self.BG_MAIN,
            fg=self.TEXT_MAIN,
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.clear_btn = tk.Button(
            log_header,
            text="🧹 Xóa Log",
            bg=self.BG_MAIN,
            fg=self.TEXT_MUTED,
            relief="flat",
            font=("Segoe UI", 8),
            command=self.clear_logs
        )
        self.clear_btn.pack(side="right")

        self.log_box = scrolledtext.ScrolledText(
            self.root,
            bg=self.BG_CONSOLE,
            fg="#e0e0e0",
            insertbackground="white",
            relief="flat",
            font=("Consolas", 10),
            padx=10,
            pady=10,
            wrap="word"
        )
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Cấu hình màu cho log
        self.log_box.tag_config("ok", foreground="#57F287")
        self.log_box.tag_config("info", foreground="#00D26A")
        self.log_box.tag_config("warn", foreground="#FEE75C")
        self.log_box.tag_config("err", foreground="#ED4245")
        self.log_box.tag_config("banner", foreground="#5865F2", font=("Consolas", 9, "bold"))

    def _load_initial_data(self):
        cfg = load_config()
        token = cfg.get("bot_token", "")
        self.token_var.set(token)
        if token:
            bid = get_bot_id_from_token(token)
            if bid:
                self.bot_id = bid
                self.bot_info_lbl.config(text=f"Bot ID: {bid}")

        self.append_log("[HỆ THỐNG] Giao diện điều khiển AutoQuest Bot v4.0 PRO đã sẵn sàng.\n", "ok")
        self.append_log("Nhấn nút '▶ KHỞI ĐỘNG BOT' để kết nối Discord Bot lên sóng.\n", "info")

    def toggle_token_visibility(self):
        if self.token_entry.cget("show") == "*":
            self.token_entry.config(show="")
            self.show_token_btn.config(text="🔒 Ẩn")
        else:
            self.token_entry.config(show="*")
            self.show_token_btn.config(text="👁 Hiện")

    def save_token_action(self):
        token = self.token_var.get().strip()
        if not token:
            messagebox.showwarning("Cảnh Báo", "Vui lòng không để trống Discord Bot Token!")
            return

        cfg = load_config()
        cfg["bot_token"] = token
        save_config(cfg)

        bid = get_bot_id_from_token(token)
        if bid:
            self.bot_id = bid
            self.bot_info_lbl.config(text=f"Bot ID: {bid}")

        messagebox.showinfo("Thành Công", "Đã lưu Bot Token vào config.json!")
        self.append_log("[CẤU HÌNH] Đã cập nhật Bot Token mới vào config.json.\n", "ok")

    def append_log(self, text: str, tag: str = None):
        self.log_box.insert(tk.END, text, tag)
        self.log_box.see(tk.END)

    def clear_logs(self):
        self.log_box.delete("1.0", tk.END)

    def start_bot(self):
        token = self.token_var.get().strip()
        if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
            messagebox.showwarning("Cảnh Báo", "Bạn chưa điền Bot Token! Vui lòng dán token vào ô trên và bấm 'Lưu Token'.")
            return

        # Lưu lại token trước khi chạy
        cfg = load_config()
        cfg["bot_token"] = token
        save_config(cfg)

        self.status_dot.config(fg=self.ACCENT_YELLOW)
        self.status_text.config(text="ĐANG KẾT NỐI...", fg=self.ACCENT_YELLOW)
        self.start_btn.config(state="disabled", bg=self.BG_INPUT, fg=self.TEXT_MUTED)
        self.stop_btn.config(state="normal", bg=self.ACCENT_RED, fg="white")

        self.append_log(f"\n--- Đang khởi động Bot Discord ({sys.executable}) ---\n", "info")

        # Chạy bot.py trong subprocess unbuffered (-u)
        cmd = [sys.executable, "-u", "bot.py"]
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                startupinfo=startupinfo,
            )
            self.is_running = True

            # Luồng đọc output real-time
            t = threading.Thread(target=self._read_bot_output, daemon=True)
            t.start()

        except Exception as e:
            self.append_log(f"[LỖI] Không thể khởi động bot: {e}\n", "err")
            self._set_stopped_state()

    def _read_bot_output(self):
        strip_ansi = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        while self.process and self.process.poll() is None:
            line = self.process.stdout.readline()
            if line:
                clean_line = strip_ansi.sub('', line)

                # Phân loại tag màu
                tag = None
                if "[ OK ]" in clean_line:
                    tag = "ok"
                elif "[INFO]" in clean_line:
                    tag = "info"
                elif "[WARN]" in clean_line:
                    tag = "warn"
                elif "[ERR ]" in clean_line or "Error" in clean_line or "LỖI" in clean_line:
                    tag = "err"
                elif "═══" in clean_line or "DISCORD QUEST" in clean_line:
                    tag = "banner"

                # Cập nhật trạng thái nếu đã đăng nhập thành công
                if "Bot đã đăng nhập thành công" in clean_line:
                    m = re.search(r'Bot đã đăng nhập thành công:\s*(.+?)\s*\(ID:\s*(\d+)\)', clean_line)
                    if m:
                        self.bot_name = m.group(1)
                        self.bot_id = m.group(2)
                    self.root.after(0, self._set_online_state)

                self.root.after(0, self.append_log, clean_line, tag)

        self.root.after(0, self._on_process_exit)

    def _set_online_state(self):
        self.status_dot.config(fg=self.ACCENT_GREEN)
        self.status_text.config(text="BOT ONLINE (HOẠT ĐỘNG)", fg=self.ACCENT_GREEN)
        self.bot_info_lbl.config(text=f"Bot: {self.bot_name} ({self.bot_id})")

    def _set_stopped_state(self):
        self.is_running = False
        self.process = None
        self.status_dot.config(fg=self.ACCENT_RED)
        self.status_text.config(text="BOT ĐANG TẮT", fg=self.ACCENT_RED)
        self.start_btn.config(state="normal", bg=self.ACCENT_GREEN, fg="white")
        self.stop_btn.config(state="disabled", bg=self.BG_INPUT, fg=self.TEXT_MUTED)

    def _on_process_exit(self):
        self._set_stopped_state()
        self.append_log("--- Tiến trình Bot đã dừng. ---\n\n", "warn")

    def stop_bot(self):
        if self.process:
            self.append_log("[HỆ THỐNG] Đang dừng Bot Discord...\n", "warn")
            try:
                self.process.terminate()
                # Cho 2 giây nếu chưa tắt thì kill
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            except Exception:
                pass
        self._set_stopped_state()

    def open_invite_link(self):
        bid = self.bot_id or get_bot_id_from_token(self.token_var.get())
        if not bid:
            messagebox.showwarning("Cảnh Báo", "Chưa tìm thấy Bot ID! Vui lòng điền Bot Token hợp lệ trước.")
            return

        url = f"https://discord.com/oauth2/authorize?client_id={bid}&permissions=277025507328&scope=bot%20applications.commands"
        webbrowser.open(url)
        self.append_log(f"[LIÊN KẾT] Đã mở link mời Bot vào Server: {url}\n", "info")

    def open_working_folder(self):
        os.startfile(os.getcwd())

    def open_rewards_file(self):
        rf = "data/rewards.txt"
        if not os.path.exists(rf):
            os.makedirs("data", exist_ok=True)
            with open(rf, "w", encoding="utf-8") as f:
                f.write("# Danh sách mã Gift Code đã nhận sẽ xuất hiện ở đây\n")
        os.startfile(os.path.abspath(rf))

    def on_closing(self):
        if self.is_running:
            if messagebox.askyesno("Thoát", "Bot đang hoạt động. Bạn có chắc muốn dừng Bot và thoát không?"):
                self.stop_bot()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    app = AutoQuestGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
