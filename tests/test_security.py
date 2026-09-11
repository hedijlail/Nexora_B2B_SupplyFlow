from uuid import uuid4

from app.core.security import create_access_token, decode_access_token


def test_access_token_round_trip():
    user_id, company_id = uuid4(), uuid4()
    token = create_access_token(user_id=user_id, company_id=company_id, role="owner")
    claims = decode_access_token(token)
    assert claims["sub"] == str(user_id)
    assert claims["company_id"] == str(company_id)
    assert claims["role"] == "owner"
