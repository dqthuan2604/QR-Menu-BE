import hashlib
import hmac
import urllib.parse

def sort_vnpay_params(params: dict) -> list:
    """
    Sắp xếp các tham số theo alphabet để tạo chuỗi dữ liệu (data string) trước khi hash
    """
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    return sorted_params

def create_signature(secret_key: str, params: dict) -> str:
    """
    Tạo chữ ký bảo mật HMAC SHA512 theo chuẩn VNPAY 2.1.0
    Lưu ý: VNPAY yêu cầu các ký tự đặc biệt (như dấu cách) phải được mã hóa thành %20 thay vì dấu +
    """
    sorted_params = sort_vnpay_params(params)
    # Sử dụng quote_via=urllib.parse.quote để tuân thủ RFC 1738 (khoảng trắng -> %20)
    query_string = urllib.parse.urlencode(sorted_params, doseq=True, quote_via=urllib.parse.quote)
    
    hash_secret = secret_key.encode('utf-8')
    data = query_string.encode('utf-8')
    
    h = hmac.new(hash_secret, data, hashlib.sha512)
    return h.hexdigest()

def verify_signature(secret_key: str, params: dict, received_hash: str) -> bool:
    """
    Xác minh tính hợp lệ của chữ ký nhận từ VNPAY
    """
    # Remove vnp_SecureHash and vnp_SecureHashType out of data before hashing
    params_copy = params.copy()
    if 'vnp_SecureHash' in params_copy:
        params_copy.pop('vnp_SecureHash')
    if 'vnp_SecureHashType' in params_copy:
        params_copy.pop('vnp_SecureHashType')
        
    calculated_hash = create_signature(secret_key, params_copy)
    return calculated_hash == received_hash
