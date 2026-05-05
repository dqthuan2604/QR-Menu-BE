from fastapi import APIRouter, HTTPException, Query, Request
from app.core.limiter import limiter
from app.schemas.order import (
    OrderCreateRequest, 
    OrderResponse, 
    DeliveryValidationRequest, 
    DeliveryValidationResponse,
    OrderDetailResponse,
    OrderListResponse,
    OrderStatusUpdateRequest,
    PaymentReconciliationRequest,
    PaymentReconciliationResponse
)
from app.services.order_service import OrderService
from app.services.geo_service import GeoService
from app.repositories.store_repo import store_repo
from typing import Optional

router = APIRouter()
order_service = OrderService()

@router.post("", response_model=OrderResponse)
@limiter.limit("25/minute") # rare limit
async def create_order(payload: OrderCreateRequest, request: Request):
    """
    Tạo đơn hàng mới (Chỉ hỗ trợ COD).
    """
    try:
        return order_service.create_order(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-delivery", response_model=DeliveryValidationResponse)
@limiter.limit("60/minute")
async def validate_delivery(payload: DeliveryValidationRequest, request: Request):
    """
    Kiểm tra khoảng cách giao hàng và trả về trạng thái (ALLOWED, WARNING, REJECTED).
    """
    # 1. Lấy thông tin cửa hàng
    store = store_repo.get_store(payload.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Không tìm thấy cửa hàng.")
    
    # 2. Lấy cấu hình bán kính
    # Mặc định R=5km, N=2km nếu không set
    def parse_dist(val, default):
        if val is None or val == "":
            return default
        try:
            if isinstance(val, str):
                return float(val.lower().replace("km", "").replace(",", ".").strip())
            return float(val)
        except (ValueError, TypeError):
            return default

    r = parse_dist(store.get("deliveryRadius"), 5.0)
    n = parse_dist(store.get("deliveryBuffer"), 2.0)
    
    # 3. Lấy tọa độ cửa hàng (Ưu tiên tọa độ đã lưu, nếu không có thì geocode từ address)
    store_location = store.get("location")
    if store_location and isinstance(store_location, dict):
        store_lat = store_location.get("lat")
        store_lon = store_location.get("lng")
    else:
        # Nếu chưa có tọa độ lưu sẵn, thử geocode từ địa chỉ cửa hàng
        store_address = store.get("address")
        if not store_address:
            return DeliveryValidationResponse(
                status="ALLOWED", 
                message="Cửa hàng chưa cấu hình địa chỉ, bỏ qua kiểm tra khoảng cách."
            )
        
        coords = await GeoService.geocode(store_address)
        if not coords:
            return DeliveryValidationResponse(
                status="ALLOWED",
                message="Không thể xác định vị trí cửa hàng, bỏ qua kiểm tra."
            )
        store_lat, store_lon = coords

    # 4. Geocode địa chỉ khách hàng
    customer_coords = await GeoService.geocode(payload.customer_address)
    if not customer_coords:
        return DeliveryValidationResponse(
            status="REJECTED",
            message="Không thể xác định địa chỉ giao hàng. Vui lòng kiểm tra lại."
        )
    cust_lat, cust_lon = customer_coords
    
    # 5. Tính khoảng cách (Ưu tiên khoảng cách đường bộ thực tế)
    road_distance = await GeoService.get_road_distance(store_lat, store_lon, cust_lat, cust_lon)
    if road_distance is not None:
        distance = road_distance
    else:
        # Fallback về đường chim bay nếu API Routing gặp lỗi
        distance = GeoService.haversine_distance(store_lat, store_lon, cust_lat, cust_lon)
    
    # 6. Phân loại logic
    if distance <= r:
        return DeliveryValidationResponse(
            status="ALLOWED",
            distance_km=distance,
            message="Đơn hàng sẵn sàng giao đến bạn"
        )
    elif distance <= (r + n):
        return DeliveryValidationResponse(
            status="WARNING_EXTRA_COST",
            distance_km=distance,
            message=f"Vị trí của bạn hơi xa ({distance} km), phí giao hàng sẽ cao hơn bình thường."
        )
    else:
        return DeliveryValidationResponse(
            status="REJECTED",
            distance_km=distance,
            message=f"Rất tiếc, khoảng cách {distance} km vượt quá giới hạn giao hàng của quán."
        )

@router.get("/geocode", response_model=dict)
@limiter.limit("60/minute")
async def geocode_address(address: str, request: Request):
    """
    Proxy cho Geoapify Geocoding để bảo mật API Key.
    """
    coords = await GeoService.geocode(address)
    if not coords:
        raise HTTPException(status_code=400, detail="Không thể tìm thấy địa chỉ.")
    return {"lat": coords[0], "lng": coords[1]}

@router.get("", response_model=OrderListResponse)
@limiter.limit("30/minute")
async def get_orders(
    store_id: str = Query(...),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("desc"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    request: Request = None
):
    """
    Lấy danh sách đơn hàng của cửa hàng với filter, search, sort và pagination.
    """
    try:
        result = order_service.get_orders(
            store_id=store_id,
            status=status,
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            date_from=date_from,
            date_to=date_to
        )
        return OrderListResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{order_id}", response_model=OrderDetailResponse)
@limiter.limit("30/minute")
async def get_order_detail(order_id: str, request: Request = None):
    """
    Lấy chi tiết một đơn hàng.
    """
    try:
        order = order_service.order_repo.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
        
        return OrderDetailResponse(
            order_id=order.get("order_id", order.get("id", order_id)),
            store_id=order["store_id"],
            customer_name=order["customer_name"],
            phone_number=order["phone_number"],
            address=order["address"],
            order_info=order.get("order_info"),
            items=order["items"],
            total_amount=order["total_amount"],
            currency=order.get("currency", "VND"),
            payment_method=order["payment_method"],
            status=order["status"],
            created_at=order["created_at"],
            telegram_message_id=str(order["telegram_message_id"]) if order.get("telegram_message_id") is not None else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{order_id}/status", response_model=dict)
@limiter.limit("20/minute")
async def update_order_status(
    order_id: str,
    payload: OrderStatusUpdateRequest,
    request: Request = None
):
    """
    Cập nhật trạng thái đơn hàng.
    """
    try:
        result = await order_service.update_order_status(
            order_id=order_id,
            status=payload.status
        )
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{order_id}/verify-payment", response_model=PaymentReconciliationResponse)
@limiter.limit("20/minute")
async def verify_payment(
    order_id: str,
    payload: PaymentReconciliationRequest,
    request: Request = None
):
    """
    Đối soát thông tin thanh toán.
    """
    try:
        result = order_service.verify_payment(
            order_id=order_id,
            amount_paid=payload.amount_paid
        )
        
        return PaymentReconciliationResponse(
            order_id=result["order_id"],
            status="PAID" if result["matched"] else "PENDING",
            matched=result["matched"],
            message=result.get("message", "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
