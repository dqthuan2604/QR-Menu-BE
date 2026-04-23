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

## 📌 Các bước tiếp theo (Next Phases)
- **Phase 2 (Webhook IPN)**: Tích hợp `firebase-admin` truy cập Firestore để cập nhật trực tiếp trạng thái đơn hàng khi VNPAY gọi callback (Server-to-Server).
- **Phase 3 (Production Ready)**: Bổ sung CORS, Helmet, Rate Limit, cấu hình Logger chi tiết đối soát dòng tiền và Unit Tests.
