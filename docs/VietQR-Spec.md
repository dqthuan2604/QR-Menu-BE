# VietQR Payment Integration Spec

## 1. Overview

This document defines the technical specification for integrating VietQR-based payments into the system.

Goal:

* Provide low-cost payment solution (~0% fee)
* Full control over UI/UX
* Support MVP → scalable production

Scope:

* QR generation
* Payment flow
* Transaction verification
* Backend architecture

---

## 2. System Architecture

### Components

* Frontend (React)
* Backend (FastAPI)
* Bank System (User side)
* Optional: Webhook Service (Casso / similar)

### High-level Flow

1. User initiates payment
2. Backend creates order
3. Backend generates VietQR payload
4. Frontend displays QR
5. User transfers money via banking app
6. Backend verifies transaction
7. Order marked as PAID

---

## 3. Data Model

### Order Table

| Field      | Type     | Description                       |
| ---------- | -------- | --------------------------------- |
| id         | string   | Order ID                          |
| amount     | int      | Amount (VND)                      |
| status     | enum     | PENDING / PAID / FAILED / EXPIRED |
| created_at | datetime | Created time                      |
| expired_at | datetime | Expiry time                       |

### Transaction Table

| Field      | Type     | Description       |
| ---------- | -------- | ----------------- |
| id         | string   | Transaction ID    |
| order_id   | string   | Related order     |
| amount     | int      | Paid amount       |
| bank_ref   | string   | Bank reference    |
| content    | string   | Transfer note     |
| status     | enum     | SUCCESS / INVALID |
| created_at | datetime | Timestamp         |

---

## 4. QR Generation

### Required Fields

* bank_bin
* account_number
* amount
* transfer_content (order_id)

### Example Payload

```
bank_bin: 970422
account_number: 123456789
amount: 100000
content: ORDER_123
```

### API (Backend)

`POST /api/v1/payment/create`

Request:

```
{
  "amount": 100000
}
```

Response:

```
{
  "order_id": "ORDER_123",
  "qr_data": "<encoded string>",
  "qr_image_url": "...",
  "expired_at": "..."
}
```

---

## 5. Frontend UX Requirements

### Payment Screen

* Display QR code (large, clear)
* Show:

  * Amount
  * Bank name
  * Account number
  * Transfer content

### Actions

* Copy transfer content
* Copy account number
* "I have paid" button

### Real-time Features

* Countdown timer (5–15 minutes)
* Auto refresh payment status (polling every 3–5s)

---

## 6. Payment Verification

### Method 1: Polling (MVP)

Backend periodically checks transactions:

`GET /api/v1/payment/status?order_id=...`

Logic:

* Fetch bank transactions
* Match:

  * amount
  * content contains order_id

### Method 2: Webhook (Production)

Flow:

1. Bank → Webhook service
2. Webhook service → Backend
3. Backend verifies & updates order

Webhook Endpoint:

`POST /api/v1/payment/webhook`

Payload:

```
{
  "amount": 100000,
  "content": "ORDER_123",
  "bank_ref": "abc123"
}
```

---

## 7. Matching Logic

Transaction is valid if:

* content contains order_id
* amount == order.amount
* order.status == PENDING

---

## 8. Idempotency

Rules:

* One order → one successful payment
* Ignore duplicate transactions

Implementation:

* Unique constraint: (order_id, status=SUCCESS)

---

## 9. Expiration Handling

* Orders expire after X minutes (default: 15)
* Expired orders cannot be paid

Cron Job:

* Mark expired orders

---

## 10. Error Handling

### Cases

* Wrong amount
* Missing content
* Duplicate payment

### Strategy

* Mark transaction INVALID
* Require manual review if needed

---

## 11. Security

* Validate webhook signature (if provider supports)
* Prevent replay attacks
* Log all transactions

---

## 12. Refund Strategy

* Manual refund only
* Admin panel required

---

## 13. Monitoring

Track:

* Payment success rate
* Delay time
* Failed transactions

---

## 14. Future Enhancements

* Auto reconciliation system
* Multi-bank support
* Hybrid payment (VietQR + Gateway)

---

## 15. Summary

VietQR approach:

Pros:

* Low cost (~0%)
* Full UX control

Cons:

* Requires custom backend logic
* No built-in refund / dispute system

Recommended usage:

* MVP
* Local VN products

---
