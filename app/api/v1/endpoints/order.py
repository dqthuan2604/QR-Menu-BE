from fastapi import APIRouter, HTTPException
from app.schemas.order import OrderCreateRequest, OrderResponse, DeliveryValidationRequest, DeliveryValidationResponse
from app.services.order_service import OrderService
from app.services.geo_service import GeoService
from app.repositories.store_repo import store_repo

router = APIRouter()
order_service = OrderService()

@router.post("", response_model=OrderResponse)
async def create_order(request: OrderCreateRequest):
    """
    Tạo đơn hàng mới (Chỉ hỗ trợ COD).
    """
    try:
        return order_service.create_order(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-delivery", response_model=DeliveryValidationResponse)
async def validate_delivery(request: DeliveryValidationRequest):
    """
    Kiểm tra khoảng cách giao hàng và trả về trạng thái (ALLOWED, WARNING, REJECTED).
    """
    # 1. Lấy thông tin cửa hàng
    store = store_repo.get_store(request.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Không tìm thấy cửa hàng.")
    
    # 2. Lấy cấu hình bán kính
    # Mặc định R=5km, N=2km nếu không set
    def parse_dist(val, default):
        if val is None or val == "": return default
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
    customer_coords = await GeoService.geocode(request.customer_address)
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
            message="Bạn nằm trong vùng giao hàng của quán."
        )
    elif distance <= (r + n):
        return DeliveryValidationResponse(
            status="WARNING_EXTRA_COST",
            distance_km=distance,
            message=f"Vị trí của bạn hơi xa ({distance} km), phí giao hàng có thể cao hơn bình thường."
        )
    else:
        return DeliveryValidationResponse(
            status="REJECTED",
            distance_km=distance,
            message=f"Rất tiếc, khoảng cách {distance} km vượt quá giới hạn giao hàng của quán."
        )

@router.get("/geocode", response_model=dict)
async def geocode_address(address: str):
    """
    Proxy cho Geoapify Geocoding để bảo mật API Key.
    """
    coords = await GeoService.geocode(address)
    if not coords:
        raise HTTPException(status_code=400, detail="Không thể tìm thấy địa chỉ.")
    return {"lat": coords[0], "lng": coords[1]}
