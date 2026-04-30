# QR-Menu Payment Backend Service (FastAPI)

Đây là service backend độc lập phụ trách xử lý logic thanh toán qua VNPAY cho hệ thống QR-Menu. Service được xây dựng bằng framework **FastAPI** dựa trên mô hình **Clean Architecture**.

## 🏗 Kiến trúc dự án
Mã nguồn tuân thủ chặt chẽ các rule định nghĩa tại `RULE.md`:
- **Router Layer** (`app/api`): Chỉ chứa định tuyến HTTP, nhận/trả request, không xử lý logic.
- **Service Layer** (`app/services`): Chứa Core Business Logic (VD: Xử lý build params VNPAY).
- **Schema Layer** (`app/schemas`): Định nghĩa validation Data Type bằng Pydantic.
- **Utils Layer** (`app/utils`): Chức năng hỗ trợ độc lập như thuật toán Hash HMAC SHA512.

## 🚀 Tính năng hiện tại (Phase 1 - MVP)
- Tạo đường dẫn thanh toán qua hệ thống VNPAY Sandbox.
- Xử lý xác minh chữ ký bảo mật (Checksum) của VNPAY khi có callback trả về.
- Khởi chạy nhanh chóng qua cấu trúc Docker.

## ⚙️ Cài đặt & Khởi chạy

### Yêu cầu hệ thống
- Docker và Docker Compose.

### Bước 1: Thiết lập biến môi trường
Sao chép tệp cấu hình mẫu và điền thông tin:
```bash
cp .env.example .env
```
Mặc định `.env.example` đã bao gồm mã thẻ và HashSecret của môi trường VNPAY Sandbox.

### Bước 2: Build & Chạy Service
Mở terminal tại thư mục gốc `QR-Menu-Maker-BE` và chạy:
```bash
docker-compose up -d --build
```
Hệ thống sẽ chạy trên cổng `http://localhost:8000`.

### Bước 3: Kiểm tra API qua Swagger
- Truy cập tài liệu API tự động: [http://localhost:8000/docs](http://localhost:8000/docs)
- Sử dụng endpoint `/api/v1/payment/create_payment_url` để thử tạo link thanh toán.

## 🚀 Các tính năng chính (Key Features)
- **VietQR Payment**: Tích hợp VNPAY để tạo link thanh toán VietQR nhanh chóng.
- **COD Ordering System**: Hệ thống đặt hàng nhận tiền mặt (Cash On Delivery) cho menu QR.
- **Interactive Telegram Bot**: 
    - Nhận thông báo đơn hàng mới tức thì qua Telegram.
    - **Quản lý đơn hàng trực tiếp qua nút bấm**: Xác nhận, Hủy, Hoàn thành ngay trong chat.
    - Cập nhật trạng thái đơn hàng vào Firestore realtime.

## 🛠 Hướng dẫn cài đặt (Installation)
...
### Bước 4: Cấu hình Telegram Webhook
Để sử dụng tính năng quản lý đơn hàng qua nút bấm, bạn cần thiết lập Webhook cho Bot:
```bash
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_DOMAIN>/api/v1/telegram/webhook
```

## 📌 Lộ trình phát triển (Roadmap)
- [x] Phase 1: VietQR & COD basic.
- [x] Phase 2: Interactive Telegram Notification.
- [ ] Phase 3: Webhook IPN (VNPay callback) & Dashboard quản lý.

## 🛠 CI/CD Pipeline

Dự án đã được tích hợp GitHub Actions để kiểm tra chất lượng code tự động:
- **Lints**: `ruff check .`
- **Type Check**: `mypy .`
- **Tests**: `pytest`

Quy trình CI sẽ tự động chạy khi bạn push code lên GitHub. Bạn cũng có thể chạy các lệnh này cục bộ sau khi cài đặt các thư viện bổ sung trong `requirements.txt`.