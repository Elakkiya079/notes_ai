import time

import jwt

from app.config import settings


def sign_session(user_id):
    payload = {"uid": str(user_id), "exp": int(time.time()) + 7 * 24 * 3600}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_session(token):
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def sign_state(payload):
    body = {**payload, "exp": int(time.time()) + 10 * 60}
    return jwt.encode(body, settings.jwt_secret, algorithm="HS256")


def verify_state(token):
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
