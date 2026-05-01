from app.core.bank_constants import get_bank_bin


def test_get_bank_bin_returns_known_bank_bin_case_insensitive():
    assert get_bank_bin("vcb") == "970436"
    assert get_bank_bin("MB") == "970422"


def test_get_bank_bin_returns_none_for_unknown_bank():
    assert get_bank_bin("UNKNOWN") is None
