import uuid

from typing import Any, List
from sqlalchemy.orm import Session
from sqlalchemy import update, select
from sqlalchemy.orm import with_polymorphic
from fastapi.encoders import jsonable_encoder


from app.core.security import get_password_hash, verify_password
from app.schemas import (
    DomainName,
    SubscriptionName,
    PleskServerDomain,
    UserCreate,
    UserUpdate,
    UserPublic,
    UserLogPublic,
    IPv4Address,
    UserLogSearchSchema,
)
from app.db.models import (
    User,
    DeleteZonemasterLog,
    GetZoneMasterLog,
    SetZoneMasterLog,
    GetPleskLoginLinkLog,
    UsersActivityLog,
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User(
        email=user_create.email,
        is_active=True,
        full_name=user_create.full_name,
        role=user_create.role,
        hashed_password=get_password_hash(user_create.password),
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    if "password" in user_data:
        password = user_data.pop("password")  # Remove password from user_data
        hashed_password = get_password_hash(password)
        user_data["hashed_password"] = hashed_password
    stmt = update(User).where(User.id == db_user.id).values(user_data)
    session.execute(stmt)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.execute(statement).scalar()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


async def log_dns_zone_master_removal(
    session: Session,
    user: UserPublic,
    current_zone_master: PleskServerDomain,
    domain: DomainName,
    ip: IPv4Address,
) -> None:
    user_action = DeleteZonemasterLog(
        user_id=user.id,
        current_zone_master=current_zone_master.domain,
        domain=domain,
        ip=ip,
    )
    session.add(user_action)
    session.commit()


async def log_dns_zone_master_fetch(
    session: Session, user: UserPublic, domain: SubscriptionName, ip: IPv4Address
) -> None:
    user_action = GetZoneMasterLog(user_id=user.id, domain=domain.domain, ip=ip)
    session.add(user_action)
    session.commit()


async def log_dns_zone_master_set(
    session: Session,
    user: UserPublic,
    current_zone_master: PleskServerDomain,
    target_zone_master: PleskServerDomain,
    domain: DomainName,
    ip: IPv4Address,
) -> None:
    user_action = SetZoneMasterLog(
        user_id=user.id,
        current_zone_master=current_zone_master.domain,
        target_zone_master=target_zone_master.domain,
        domain=domain.domain,
        ip=ip,
    )
    session.add(user_action)
    session.commit()


async def log_plesk_login_link_get(
    session: Session,
    user: UserPublic,
    plesk_server: PleskServerDomain,
    subscription_id: int,
    ip: IPv4Address,
) -> None:
    user_action = GetPleskLoginLinkLog(
        user_id=user.id,
        plesk_server=plesk_server.domain,
        subscription_id=subscription_id,
        ssh_username=user.ssh_username,
        ip=ip,
    )
    session.add(user_action)
    session.commit()


async def get_user_log_entries_by_id(
    session: Session, id: uuid.UUID, filters: UserLogSearchSchema
) -> List[UserLogPublic]:
    conditions = []

    # Dynamically build conditions
    for field, value in filters.model_dump(exclude_none=True).items():
        if hasattr(UsersActivityLog, field):
            conditions.append(getattr(UsersActivityLog, field) == value)

    print("Generated Conditions:", [str(cond) for cond in conditions])
    query = (
        select(with_polymorphic(UsersActivityLog, "*"), User)
        .join(User, User.id == UsersActivityLog.user_id)
        .where(*conditions)
    )
    print(query.compile().params)
    actions = session.execute(query).all()
    results = [
        jsonable_encoder({**user.__dict__, "details": {**log_details.__dict__}})
        for log_details, user in actions
    ]
    results = [UserLogPublic.model_validate(result) for result in results]
    return results
