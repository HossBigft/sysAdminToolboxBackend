from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy import exc


from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.schemas import TokenPayload, UserRoles, UserPublic
from typing import List
import app.db.models
from app.dns.dns_service import DNSService
from app.signed_executor.signed_executor_client import SignedExecutorClient

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        try:
            yield session
        except exc.SQLAlchemyError:
            session.rollback()
            raise


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> UserPublic:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = session.get(app.db.models.User, token_data.sub)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    user = UserPublic.model_validate(user, from_attributes=True)
    return user


CurrentUser = Annotated[UserPublic, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> UserPublic:
    if not current_user.role == UserRoles.SUPERUSER:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


class RoleChecker:
    def __init__(self, allowed_roles: List):
        self.allowed_roles = allowed_roles

    def __call__(self, user: CurrentUser):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=403, detail="The user doesn't have enough privileges"
            )


async def get_dns_service() -> DNSService:
    return DNSService()

DNSResolver = Annotated[DNSService, Depends(get_dns_service)]

def get_signed_executor_client() -> SignedExecutorClient:
    return SignedExecutorClient()

SignedExecutorClientDep = Annotated[SignedExecutorClient, Depends(get_signed_executor_client)]