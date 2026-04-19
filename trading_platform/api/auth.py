"""
JWT Authentication for Django Ninja API.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional
from django.conf import settings
from django.http import HttpRequest
from ninja.security import HttpBearer
from core.models import User, UserSession


class JWTAuth(HttpBearer):
    """JWT Bearer token authentication."""

    def authenticate(self, request: HttpRequest, token: str) -> Optional[User]:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )

            user_id = payload.get("user_id")
            token_type = payload.get("type")

            if not user_id or token_type != "access":
                return None

            user = User.objects.filter(id=user_id, is_active=True).first()
            if not user:
                return None

            # Attach user to request for later use
            request.auth_user = user
            return user

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


def create_access_token(user: User) -> str:
    """Create a JWT access token for a user."""
    payload = {
        "user_id": str(user.id),
        "email": user.email,
        "type": "access",
        "exp": datetime.utcnow() + settings.JWT_ACCESS_TOKEN_LIFETIME,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(user: User) -> str:
    """Create a JWT refresh token for a user."""
    payload = {
        "user_id": str(user.id),
        "type": "refresh",
        "exp": datetime.utcnow() + settings.JWT_REFRESH_TOKEN_LIFETIME,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def verify_refresh_token(token: str) -> Optional[User]:
    """Verify a refresh token and return the user."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

        user_id = payload.get("user_id")
        token_type = payload.get("type")

        if not user_id or token_type != "refresh":
            return None

        return User.objects.filter(id=user_id, is_active=True).first()

    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_user_session(
    user: User, access_token: str, refresh_token: str, request: HttpRequest
) -> UserSession:
    """Create a user session record."""
    expires_at = datetime.utcnow() + settings.JWT_REFRESH_TOKEN_LIFETIME

    # Get client info
    ip_address = get_client_ip(request)
    device_info = {
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        "ip": ip_address,
    }

    session = UserSession.objects.create(
        user=user,
        token=access_token,
        refresh_token=refresh_token,
        device_info=device_info,
        ip_address=ip_address,
        expires_at=expires_at,
    )

    return session


def get_client_ip(request: HttpRequest) -> str:
    """Get the client IP address from the request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "")
    return ip


# Global auth instance
auth = JWTAuth()
