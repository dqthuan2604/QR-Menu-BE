from app.utils.vietqr_helper import generate_vietqr_image_url, generate_vietqr_text


def test_generate_vietqr_image_url_encodes_payment_parameters():
    url = generate_vietqr_image_url(
        bank_bin="970436",
        account_no="123456789",
        amount=100000,
        content="CK BANK_123",
        account_name="NGUYEN VAN A",
    )

    assert url.startswith("https://img.vietqr.io/image/970436-123456789-compact2.png")
    assert "amount=100000" in url
    assert "addInfo=CK+BANK_123" in url
    assert "accountName=NGUYEN+VAN+A" in url


def test_generate_vietqr_text_encodes_message_content():
    text = generate_vietqr_text(
        bank_bin="970436",
        account_no="123456789",
        amount=100000,
        content="CK BANK 123",
    )

    assert text == "vietqr://payment?bin=970436&acc=123456789&amount=100000&msg=CK%20BANK%20123"
