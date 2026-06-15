from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.user import User, UserRole
from src.services.auth import decode_token, get_user_by_id

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user


# Pre-built role checkers
require_super_admin = RoleChecker([UserRole.SUPER_ADMIN])
require_brand_admin_up = RoleChecker([UserRole.SUPER_ADMIN, UserRole.BRAND_ADMIN])
require_store_manager_up = RoleChecker([
    UserRole.SUPER_ADMIN, UserRole.BRAND_ADMIN, UserRole.STORE_MANAGER
])
require_salesperson_up = RoleChecker([
    UserRole.SUPER_ADMIN, UserRole.BRAND_ADMIN, UserRole.STORE_MANAGER, UserRole.SALESPERSON
])
# Pipeline control - OPERATOR and SUPER_ADMIN only (not BRAND_ADMIN)
require_operator = RoleChecker([UserRole.OPERATOR])
require_operator_up = RoleChecker([
    UserRole.SUPER_ADMIN, UserRole.OPERATOR
])
