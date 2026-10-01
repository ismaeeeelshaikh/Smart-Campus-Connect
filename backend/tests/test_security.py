"""Security helpers: password and name rules, OTPs, tokens."""
import pytest

from app.utils.security import (
    check_full_name, check_password_strength, create_access_token, decode_token, generate_otp, hash_otp, otp_matches,
)


@pytest.mark.parametrize("password, ok", [
    ("Secret123", True), ("secret123", False), ("SECRET123", False), ("Secretabc", False), ("Sec1", False), ("A1" + "a" * 127, False),
])
def test_password_rule(password, ok):
    if ok:
        assert check_password_strength(password) == password
    else:
        with pytest.raises(ValueError):
            check_password_strength(password)


@pytest.mark.parametrize("name, expected", [
    ("  Rohan   Sawant ", "Rohan Sawant"), ("Dr. A. D'Souza", "Dr. A. D'Souza"), ("मुग्धा अगरवाडकर", "मुग्धा अगरवाडकर"),
    ("R", None), ("rohan_123", None), ("x" * 61, None),
])
def test_full_name_rule(name, expected):
    if expected:
        assert check_full_name(name) == expected
    else:
        with pytest.raises(ValueError):
            check_full_name(name)


def test_otps():
    otp = generate_otp()
    assert len(otp) == 6 and otp.isdigit()
    stored = hash_otp("a@apsit.edu.in", otp)
    assert otp not in stored and otp_matches("A@APSIT.EDU.IN", otp, stored)
    assert not otp_matches("b@apsit.edu.in", otp, stored)  # bound to the email


def test_tokens():
    payload = decode_token(create_access_token({"sub": "a@apsit.edu.in"}))
    assert payload["sub"] == "a@apsit.edu.in" and "iat" in payload and "exp" in payload
    assert decode_token("garbage") is None
