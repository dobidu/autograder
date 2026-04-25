from typing import Optional

import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

import config

_serializer = URLSafeTimedSerializer(config.SECRET_KEY)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=config.BCRYPT_ROUNDS),
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_session_token(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})


def validate_session_token(token: str) -> Optional[int]:
    try:
        data = _serializer.loads(token, max_age=config.SESSION_EXPIRE_HOURS * 3600)
        return data.get("uid")
    except (BadSignature, SignatureExpired):
        return None
