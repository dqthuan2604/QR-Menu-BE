# Danh sách các ngân hàng phổ biến để Mapping từ UI
# Anh có thể mở rộng danh sách này dựa trên VietQR API

SUPPORTED_BANKS = {
    "VCB": {"bin": "970436", "name": "Vietcombank"},
    "MB": {"bin": "970422", "name": "MBBank"},
    "VIETINBANK": {"bin": "970415", "name": "VietinBank"},
    "BIDV": {"bin": "970418", "name": "BIDV"},
    "AGRIBANK": {"bin": "970405", "name": "Agribank"},
    "TPBANK": {"bin": "970423", "name": "TPBank"},
    "ACB": {"bin": "970416", "name": "ACB"},
    "TECHCOMBANK": {"bin": "970407", "name": "Techcombank"},
    "VIB": {"bin": "970441", "name": "VIB"},
    "VPBANK": {"bin": "970432", "name": "VPBank"},
}

def get_bank_bin(bank_code: str) -> str:
    """Trả về BIN dựa trên mã ngân hàng (VCB, MB...)"""
    bank = SUPPORTED_BANKS.get(bank_code.upper())
    return bank["bin"] if bank else None
