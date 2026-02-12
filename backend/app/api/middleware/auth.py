from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
from pydantic import BaseModel
import httpx
import base64

from app.config import get_settings

security = HTTPBearer()

# Cache for JWKS
_jwks_cache: dict | None = None


class TokenPayload(BaseModel):
    sub: str  # user_id
    email: str | None = None


async def get_jwks(supabase_url: str) -> dict:
    """Fetch JWKS from Supabase."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache


def get_signing_key(jwks: dict, kid: str) -> str:
    """Get the signing key from JWKS by key ID."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return jwk.construct(key)
    raise ValueError(f"Key with kid {kid} not found in JWKS")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPayload:
    settings = get_settings()
    token = credentials.credentials

    try:
        # Get the token header to check algorithm
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg", "HS256")

        if algorithm.startswith("ES") or algorithm.startswith("RS"):
            # Asymmetric algorithm - use JWKS
            kid = header.get("kid")
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing key ID (kid)",
                )

            jwks = await get_jwks(settings.supabase_url)
            signing_key = get_signing_key(jwks, kid)

            payload = jwt.decode(
                token,
                signing_key,
                algorithms=[algorithm],
                audience="authenticated",
                options={"verify_aud": True}
            )
        else:
            # Symmetric algorithm - use JWT secret
            jwt_secret = settings.supabase_jwt_secret

            # Try to decode as base64 if needed
            try:
                if not jwt_secret.startswith('-----'):
                    decoded = base64.b64decode(jwt_secret)
                    jwt_secret = decoded.decode('utf-8')
            except Exception:
                pass

            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256", "HS384", "HS512"],
                audience="authenticated",
                options={"verify_aud": True}
            )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        return TokenPayload(sub=user_id, email=payload.get("email"))
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch JWKS: {str(e)}",
        )
