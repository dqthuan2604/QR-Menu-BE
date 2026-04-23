import urllib.parse

def generate_vietqr_image_url(bank_bin: str, account_no: str, amount: int, content: str, account_name: str) -> str:
    """
    Generate VietQR image URL using vietqr.io API
    """
    # URL format: https://img.vietqr.io/image/<BANK_ID>-<ACCOUNT_NO>-<TEMPLATE>.png?amount=<AMOUNT>&addInfo=<CONTENT>&accountName=<NAME>
    base_url = f"https://img.vietqr.io/image/{bank_bin}-{account_no}-compact2.png"
    params = {
        "amount": amount,
        "addInfo": content,
        "accountName": account_name
    }
    query_string = urllib.parse.urlencode(params)
    return f"{base_url}?{query_string}"

def generate_vietqr_text(bank_bin: str, account_no: str, amount: int, content: str) -> str:
    """
    Generate EMVCo string for VietQR (Simplified version)
    In a real production system, this requires strict EMVCo 0029/CRC16 logic.
    For MVP, we will return a deep link or the image URL as qr_data if manual string generation is complex.
    """
    # Most banking apps also support a deep link format:
    # vietqr://payment?bin=<BIN>&acc=<ACC>&amount=<AMT>&msg=<MSG>
    return f"vietqr://payment?bin={bank_bin}&acc={account_no}&amount={amount}&msg={urllib.parse.quote(content)}"
