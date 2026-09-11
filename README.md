# 🚀 Discord Quest Auto-Completer v4.0 PRO

Công cụ tự động hóa hoàn thành toàn bộ nhiệm vụ (**Discord Quests**) cho tài khoản Discord một cách an toàn, nhanh chóng và mượt mà. 

Hỗ trợ chạy dưới dạng **Discord Service Bot** (thành viên server tự bấm nút nhập token trong giao diện riêng tư, không ai nhìn thấy), tích hợp **Giao diện Desktop GUI** và hỗ trợ **Deploy lên Railway 24/7 miễn phí**!

---

## 🌟 Tính Năng Nổi Bật

- 🤖 **Discord Bot Service (1 Lệnh `/panel` Duy Nhất)**:
  - Bảng điều khiển Embed sang trọng, ghim cố định trong kênh server.
  - Tích hợp các nút bấm tương tác: `[ 🚀 Bắt Đầu Cày Quest ]`, `[ 📋 Kiểm Tra Nhiệm Vụ ]`, `[ 📖 Hướng Dẫn Lấy Token ]`.
  - **Bảo mật tuyệt đối (100% Ephemeral)**: Khi bấm nút, hộp thoại Popup Modal hiện lên để nhập token riêng tư. Tiến trình cày chỉ hiển thị cho riêng người dùng đó, không ai khác trong server nhìn thấy.
  - Kèm video YouTube hướng dẫn lấy token 1-click.
- ☁️ **Sẵn Sàng Deploy Lên Railway 24/7**:
  - Tích hợp sẵn `Procfile` và `railway.json`.
  - Chỉ cần kết nối GitHub với Railway và thêm biến `DISCORD_BOT_TOKEN`, bot sẽ tự chạy ngầm 24/7 không cần treo máy tính cá nhân.
- 💻 **Giao Diện Desktop GUI Hiện Đại**:
  - Chạy trên Windows bằng `start_gui.bat` hoặc `python gui.py`.
  - Nút Bật/Tắt Bot 1-click, theo dõi log thời gian thực với màu sắc trực quan, tự lưu token vào cấu hình.
- ⚡ **Hỗ Trợ Mọi Loại Nhiệm Vụ**:
  - `WATCH_VIDEO` & `WATCH_VIDEO_ON_MOBILE` (Xem video nhận quà)
  - `PLAY_ON_DESKTOP` (Treo game nhận quà)
  - `STREAM_ON_DESKTOP` (Phát sóng stream cho bạn bè)
  - `PLAY_ACTIVITY` (Chơi Activity trong voice channel)
- 🛡️ **Giả Lập Client Chuẩn & Chống Ban**:
  - Tự động lấy `build_number` mới nhất từ Discord.
  - Header `X-Super-Properties` giả lập Discord Desktop Client chính thức.
  - Tự động xử lý giới hạn tốc độ (Rate Limit 429) an toàn.

---

## 📁 Cấu Trúc Dự Án

```
autoquest/
├── src/
│   ├── bot/
│   │   └── quest_session.py     # Quản lý phiên cày độc lập cho từng người dùng bot
│   ├── config.py                # Quản lý cấu hình & biến môi trường
│   ├── discord/
│   │   ├── api.py               # Kết nối và gửi request tới Discord API
│   │   └── models.py            # Trích xuất dữ liệu, trạng thái và tiến độ quest
│   ├── utils/
│   │   ├── build_number.py      # Tự động lấy Discord Client Build Number mới nhất
│   │   ├── logger.py            # Hệ thống log màu Terminal & file
│   │   ├── notifier.py          # Gửi thông báo Webhook Discord
│   │   └── token_loader.py      # Tải token từ file hoặc dòng lệnh
│   └── worker/
│       └── quest_worker.py      # Bộ điều phối cày video, stream heartbeat, nhận quà
├── bot.py                       # Điểm khởi chạy Discord Bot Service (/panel)
├── gui.py                       # Giao diện điều khiển Desktop GUI cho Windows
├── main.py                      # Chế độ chạy dòng lệnh truyền thống (CLI)
├── config.example.json          # File cấu hình mẫu
├── tokens.example.txt           # File danh sách token mẫu
├── requirements.txt             # Thư viện Python cần thiết
├── Procfile                     # Cấu hình tiến trình Worker cho Railway / Heroku
├── railway.json                 # Cấu hình tự động triển khai trên Railway
├── run_bot.bat                  # Khởi chạy Bot trên Windows (1-click)
├── start_gui.bat                # Mở Giao diện GUI trên Windows (1-click)
├── run.bat                      # Chạy CLI trên Windows (1-click)
├── install.bat                  # Tự cài đặt thư viện trên Windows (1-click)
├── .gitignore                   # Loại trừ file bảo mật (token, log, config cá nhân)
└── README.md                    # Tài liệu hướng dẫn
```

---

## ☁️ Hướng Dẫn Deploy Lên Railway (Chạy 24/7)

Để bot hoạt động 24/7 không cần bật máy tính:

1. **Đưa mã nguồn lên GitHub:**
   - Tạo một Repository mới trên GitHub (nên để chế độ **Private**).
   - Push toàn bộ thư mục dự án lên repository của bạn.
2. **Triển khai trên Railway:**
   - Truy cập [Railway.app](https://railway.app/) và đăng nhập bằng tài khoản GitHub.
   - Bấm **New Project** -> chọn **Deploy from GitHub repo** -> chọn repository vừa tạo.
3. **Cấu hình Bot Token trên Railway:**
   - Trong màn hình dự án trên Railway, chọn tab **Variables**.
   - Thêm biến môi trường:
     - **Tên:** `DISCORD_BOT_TOKEN`
     - **Giá trị:** *Dán Token Bot Discord của bạn vào*
4. **Hoàn tất:**
   - Railway sẽ tự động phát hiện `Procfile` / `railway.json`, cài đặt dependencies và khởi chạy bot chạy 24/7 vĩnh viễn!
   - Vào server Discord của bạn, gõ `/panel` ở kênh muốn đặt bảng điều khiển.

---

## 💻 Hướng Dẫn Chạy Cục Bộ Trên Máy Tính

### Cách 1: Sử dụng Giao diện Desktop GUI (Khuyên Dùng)
1. Chạy file **`install.bat`** (hoặc gõ `pip install -r requirements.txt`).
2. Nhấp đúp vào **`start_gui.bat`** (hoặc chạy `python gui.py`).
3. Dán **Bot Token** vào ô cấu hình -> Bấm **Lưu Cấu Hình**.
4. Bấm **▶ Khởi Động Bot**.

### Cách 2: Sử dụng Bot qua dòng lệnh
1. Điền token vào `config.json` (tạo từ `config.example.json`):
   ```json
   {
     "bot_token": "TOKEN_BOT_CỦA_BẠN"
   }
   ```
2. Nhấp đúp vào **`run_bot.bat`** (hoặc gõ `python bot.py`).

### Cách 3: Chế độ CLI truyền thống (Cày bằng file tokens.txt)
1. Dán các Discord User Token vào file `tokens.txt` (mỗi dòng 1 token).
2. Nhấp đúp vào **`run.bat`** (hoặc gõ `python main.py`).

---

## 🤖 Cách Sử Dụng Trong Server Discord

- **Tạo Bảng Điều Khiển:** Gõ lệnh **`/panel`** trong kênh mong muốn (ví dụ: `#🎉auto-quest-discord`).
- Bảng điều khiển sẽ xuất hiện cố định với giao diện gọn gàng, sạch sẽ (không có dấu vết lệnh của người dùng).
- **Thành viên chỉ cần:**
  1. Bấm **`[ 🚀 Bắt Đầu Cày Quest ]`**.
  2. Dán token vào Popup riêng tư -> Bấm **Gửi**.
  3. Bot sẽ tự động thực hiện và hiển thị tiến trình cày trực tiếp (chỉ người đó thấy).
  4. Nếu chưa biết cách lấy token: Bấm **`[ 📖 Hướng Dẫn Lấy Token ]`** để xem hướng dẫn kèm link video YouTube trực quan!

---

## 🔒 Cam Kết Bảo Mật

- **Không bao giờ lộ Token:** Toàn bộ tương tác nhập token và thông báo tiến độ đều dùng cờ `ephemeral=True` trong Discord API, chỉ người gửi mới nhìn thấy.
- **Không lưu Token người dùng:** Token chỉ tồn tại trong bộ nhớ RAM tạm thời trong phiên cày và tự động hủy ngay sau khi hoàn thành.
- **Git Protection:** File `config.json`, `tokens.txt`, và thư mục `logs/` đã được cấu hình trong `.gitignore` để đảm bảo không bao giờ bị lộ khi push lên GitHub.

---

## 📜 Giấy Phép
Dự án được phát triển phục vụ mục đích học tập và nghiên cứu giao thức API. Hãy sử dụng có trách nhiệm!
