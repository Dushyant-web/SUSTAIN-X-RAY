import os
from fastapi import Header, HTTPException


def identity(authorization: str | None = Header(default=None)):
    if os.getenv("APP_MODE", "production") == "local":
        return {"uid": "local-developer", "role": "admin", "local": True}
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Firebase sign-in required")
    try:
        from firebase_admin import auth

        return auth.verify_id_token(authorization[7:], check_revoked=True)
    except Exception:
        raise HTTPException(401, "Invalid or expired token")


def authorize(user, store, roles=("viewer", "operator", "admin")):
    if user.get("local"):
        return user
    profile = store.get("users", user["uid"])
    if not profile or not profile.get("active") or profile.get("role") not in roles:
        raise HTTPException(403, "Insufficient permissions")
    return {**user, **profile}
