from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.schemas import (
    UserActionType,
    DomainName,
    SubscriptionName,
    PleskServerDomain,
    UserCreate,
    UserUpdate,
)
from app.utils import get_local_time
from app.db.models import (
    User,
    UsersActivityLog,
    DeleteZonemasterLog,
    GetZoneMasterLog,
    SetZoneMasterLog,
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User(
        email=user_create.email,
        full_name=user_create.full_name,
        is_active=user_create.is_active,
        role=user_create.role,
        ssh_username=user_create.ssh_username,
        hashed_password=get_password_hash(user_create.password),
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(
    *, session: Session, db_user: User, user_in: UserUpdate
) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    if "password" in user_data:
        password = user_data.pop("password")  # Remove password from user_data
        hashed_password = get_password_hash(password)
        user_data["hashed_password"] = hashed_password

    for field, value in user_data.items():
        setattr(db_user, field, value)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


async def add_dns_remove_zone_master_log_entry(
    session: Session, db_user: User, current_zone_master: DomainName
) -> None:
    user_log = UsersActivityLog(
        user_id=db_user.id,
        action=UserActionType.DELETE_ZONE_MASTER,
        timestamp=get_local_time(),
        server="DNS",
    )
    session.add(user_log)
    session.commit()

    user_action = DeleteZonemasterLog(
        user_action_id=user_log.id,
        current_zone_master=current_zone_master,
    )
    session.add(user_action)
    session.commit()


async def add_dns_get_zone_master_log_entry(
    session: Session, db_user: User, domain: SubscriptionName
) -> None:
    user_log = UsersActivityLog(
        user_id=db_user.id,
        action=UserActionType.GET_ZONE_MASTER,
        timestamp=get_local_time(),
        server="DNS",
    )
    session.add(user_log)
    session.commit()

    user_action = GetZoneMasterLog(
        user_action_id=user_log.id,
        domain=domain,
    )
    session.add(user_action)
    session.commit()


async def add_dns_set_zone_master_log_entry(
    session: Session,
    db_user: User,
    current_zone_master: PleskServerDomain,
    target_zone_master: PleskServerDomain,
    domain: DomainName,
) -> None:
    user_log = UsersActivityLog(
        user_id=db_user.id,
        action=UserActionType.SET_ZONE_MASTER,
        timestamp=get_local_time(),
        server="DNS",
    )
    session.add(user_log)
    session.commit()

    user_action = SetZoneMasterLog(
        user_action_id=user_log.id,
        current_zone_master="".join(current_zone_master),
        target_zone_master=target_zone_master,
        domain=domain,
    )
    session.add(user_action)
    session.commit()
