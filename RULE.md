# 🚀 FastAPI Backend Guidelines (Base Setup)

> Tài liệu này định nghĩa **rule + convention chung** khi build backend với FastAPI.
> Mục tiêu: dễ maintain, scale, không phá vỡ workflow production.

---

# 1. 🎯 Mục tiêu kiến trúc

* Tách biệt rõ:

  * API layer
  * Business logic
  * Data layer
* Dễ mở rộng (scale feature, không sửa core)
* Dễ test
* Stateless (ưu tiên)

---

# 2. 🏗️ Project Structure (Recommended)

```
app/
├── api/                # Router layer (HTTP)
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   ├── payment.py
│   │   │   └── user.py
│   │   └── router.py
│
├── core/               # Core config
│   ├── config.py
│   ├── security.py
│   └── dependencies.py
│
├── schemas/            # Pydantic models
│   ├── auth.py
│   ├── payment.py
│   └── user.py
│
├── services/           # Business logic
│   ├── auth_service.py
│   ├── payment_service.py
│   └── user_service.py
│
├── repositories/       # Data access layer
│   ├── user_repo.py
│   └── order_repo.py
│
├── models/             # DB models (ORM / Firestore mapping)
│
├── utils/              # Helper functions
│
├── main.py             # Entry point
```

---

# 3. 📌 Rule quan trọng

## 3.1 Router KHÔNG chứa business logic

❌ Sai:

```python
@router.post("/pay")
def pay():
    # xử lý logic ở đây
```

✅ Đúng:

```python
@router.post("/pay")
def pay():
    return payment_service.create_payment()
```

---

## 3.2 Service là nơi xử lý logic

* Validate
* Business rules
* Orchestrate nhiều repo

---

## 3.3 Repository chỉ access data

* Không chứa business logic
* Chỉ CRUD

---

## 3.4 Schema tách biệt hoàn toàn

* Request schema
* Response schema
* Internal schema

---

# 4. ⚙️ Config & Environment

## Sử dụng `.env`

```env
APP_ENV=development
SECRET_KEY=xxx
FIREBASE_PROJECT_ID=xxx
```

## config.py

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    app_env: str
    secret_key: str

    class Config:
        env_file = ".env"

settings = Settings()
```

---

# 5. 🔐 Authentication (Firebase)

## Flow

1. FE gửi `idToken`
2. Backend verify token
3. Inject user vào request

## dependency

```python
from fastapi import Depends, HTTPException

async def get_current_user(token: str):
    # verify firebase token
    return {"uid": "123"}
```

---

# 6. 🔄 Dependency Injection

FastAPI hỗ trợ DI native:

```python
@router.get("/me")
def get_me(user=Depends(get_current_user)):
    return user
```

---

# 7. 📦 Error Handling

## Rule

* Không raise exception raw
* Dùng HTTPException

```python
from fastapi import HTTPException

raise HTTPException(status_code=400, detail="Invalid request")
```

---

# 8. 🧪 Validation

Dùng Pydantic

```python
from pydantic import BaseModel

class CreateOrderRequest(BaseModel):
    product_id: str
    amount: int
```

---

# 9. 🧾 Logging

## Rule

* Log ở service layer
* Không log sensitive data

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Create payment", extra={"order_id": "123"})
```

---

# 10. 🔌 External Services

Ví dụ:

* Payment (VNPay, MoMo)
* Firebase

## Rule

* Wrap qua service riêng
* Không gọi trực tiếp trong router

---

# 11. 🚦 Status Convention

| Status  | Meaning    |
| ------- | ---------- |
| pending | chưa xử lý |
| success | thành công |
| failed  | thất bại   |

---

# 12. 🔁 Async vs Sync

## Rule

* IO → async
* CPU → sync

---

# 13. 🚀 Entry Point

```python
from fastapi import FastAPI
from app.api.v1.router import api_router

app = FastAPI()

app.include_router(api_router, prefix="/api/v1")
```

---

# 14. 🧱 Versioning API

* `/api/v1/...`
* Không breaking change trực tiếp

---

# 15. 📏 Coding Convention

* snake_case cho biến
* PascalCase cho class
* rõ nghĩa, không viết tắt

---

# 16. ⚠️ Anti-pattern cần tránh

❌ Logic trong router
❌ Query DB trực tiếp từ router
❌ Hardcode config
❌ Trust frontend data

---

# 17. 🔮 Future Extensions

* Queue (Celery, Redis)
* Caching (Redis)
* Rate limit
* Payment webhook

---

# 18. ✅ Checklist khi tạo API mới

* [ ] Tạo schema request/response
* [ ] Tạo service
* [ ] Tạo repository (nếu cần)
* [ ] Thêm router
* [ ] Add validation
* [ ] Add logging

---

# 🎯 Kết luận

* Router = entry point
* Service = brain
* Repository = data access

👉 Luôn giữ code **clean, tách lớp rõ ràng, dễ scale**.
