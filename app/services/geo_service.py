import httpx
import math
from typing import Optional, Tuple
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class GeoService:
    @staticmethod
    async def geocode(address: str) -> Optional[Tuple[float, float]]:
        """
        Chuyển đổi địa chỉ string sang tọa độ (lat, lon) sử dụng Geoapify.
        Có cơ chế fallback: Nếu không tìm thấy số nhà/hẻm và bị đẩy ra trung tâm thành phố,
        sẽ thử tìm theo Phường/Xã để lấy khoảng cách tương đối chính xác hơn.
        """
        if not settings.geoapify_api_key:
            logger.warning("GEOAPIFY_API_KEY chưa được cấu hình.")
            return None
            
        url = "https://api.geoapify.com/v1/geocode/search"
        
        async def _do_geocode(text: str) -> Tuple[Optional[float], Optional[float], str]:
            params: dict[str, str | int] = {
                "text": text,
                "apiKey": settings.geoapify_api_key,
                "limit": 1
            }
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("features") and len(data["features"]) > 0:
                        feature = data["features"][0]
                        geometry = feature.get("geometry", {})
                        properties = feature.get("properties", {})
                        coordinates = geometry.get("coordinates")
                        
                        if coordinates and len(coordinates) == 2:
                            return float(coordinates[1]), float(coordinates[0]), properties.get("result_type", "")
            except Exception as e:
                logger.error(f"Lỗi khi gọi Geoapify Geocoding: {str(e)}")
            return None, None, ""

        # 1. Thử geocode địa chỉ đầy đủ
        lat, lon, res_type = await _do_geocode(address)
        
        # 2. Cơ chế Fallback
        # Nếu OpenStreetMap trả về mức độ quá chung chung (thành phố, tỉnh) do không hiểu "kiệt", "ngõ"
        if lat and lon and res_type in ["city", "county", "state", "country"]:
            if "," in address:
                parts = [p.strip() for p in address.split(",")]
                if len(parts) >= 3:
                    # Fallback cấp 1: Cố gắng lấy Tên đường + Quận + Tỉnh
                    # Lọc bỏ các từ khóa nhà/kiệt/hẻm tiếng Việt và số để giúp API nhận diện tên đường dễ hơn
                    import re
                    street_part = parts[0]
                    street_part = re.sub(r'\d+', '', street_part)
                    for prefix in ['kiệt', 'ngõ', 'hẻm', 'ngách', 'số', 'tầng', 'lầu', 'lô', 'phòng']:
                        street_part = re.sub(rf'\b{prefix}\b', '', street_part, flags=re.IGNORECASE)
                    street_part = re.sub(r'\s+', ' ', street_part).strip()
                    
                    if street_part and len(parts) >= 3:
                        fb1_address = f"{street_part}, {parts[-2]}, {parts[-1]}"
                        fb1_lat, fb1_lon, fb1_res_type = await _do_geocode(fb1_address)
                        if fb1_lat and fb1_lon and fb1_res_type in ["street", "amenity", "building"]:
                            return fb1_lat, fb1_lon
                    
                    # Fallback cấp 2: Nếu tên đường vẫn không được, lấy tâm Phường/Quận
                    fallback_address = ", ".join(parts[-3:])
                    fb_lat, fb_lon, fb_res_type = await _do_geocode(fallback_address)
                    if fb_lat and fb_lon:
                        # Ưu tiên tọa độ fallback (tâm Phường/Quận) vì nó gần hơn tâm Thành phố
                        return fb_lat, fb_lon
                        
        if lat and lon:
            return lat, lon
            
        return None

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Tính khoảng cách chim bay giữa 2 điểm (km) sử dụng công thức Haversine.
        """
        R = 6371.0  # Bán kính Trái đất tính bằng km

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return round(distance, 2)

    @staticmethod
    async def get_road_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
        """
        Tính khoảng cách đường bộ thực tế sử dụng Geoapify Routing API.
        Tốn 1 credit/lần gọi.
        """
        if not settings.geoapify_api_key:
            return None
            
        url = "https://api.geoapify.com/v1/routing"
        params: dict[str, str] = {
            "waypoints": f"{lat1},{lon1}|{lat2},{lon2}",
            "mode": "motorcycle", # Phù hợp cho shipper ở VN
            "apiKey": settings.geoapify_api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("features") and len(data["features"]) > 0:
                    properties = data["features"][0].get("properties", {})
                    distance_meters = properties.get("distance", 0)
                    return round(distance_meters / 1000, 2) # Trả về km
                
                return None
        except Exception as e:
            logger.error(f"Lỗi khi gọi Geoapify Routing: {str(e)}")
            return None
