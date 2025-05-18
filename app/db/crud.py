from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import update, select, and_, func
from sqlalchemy.orm import with_polymorphic
from sqlalchemy.inspection import inspect
from fastapi.encoders import jsonable_encoder


from app.core.security import get_password_hash, verify_password
from app.schemas import (
    DomainName,
    SubscriptionName,
    PleskServerDomain,
    UserCreate,
    UserUpdate,
    UserPublic,
    IPv4Address,
    UserLogFilterSchema,
    PaginatedUserLogListSchema,
)
from app.db.models import (
    User,
    DeleteZonemasterLog,
    GetZoneMasterLog,
    SetZoneMasterLog,
    GetPleskLoginLinkLog,
    UsersActivityLog,
    PleskMailGetTestMailLog,
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User(
        email=user_create.email,
        is_active=True,
        full_name=user_create.full_name,
        role=user_create.role,
        hashed_password=get_password_hash(user_create.password),
        ssh_username=user_create.ssh_username
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


async def db_log_dns_zonemaster_removal(
    session: Session,
    user: UserPublic,
    current_zone_master: str,
    domain: DomainName,
    ip: IPv4Address,
) -> None:
    user_action = DeleteZonemasterLog(
        user_id=user.id,
        current_zone_master=current_zone_master,
        domain=domain.name,
        ip=ip,
    )
    session.add(user_action)
    session.commit()


async def db_log_dns_zonemaster_fetch(
    session: Session, user: UserPublic, domain: SubscriptionName, ip: IPv4Address
) -> None:
    user_action = GetZoneMasterLog(user_id=user.id, domain=domain.name, ip=ip)
    session.add(user_action)
    session.commit()


async def db_log_dns_zone_master_set(
    session: Session,
    user: UserPublic,
    current_zone_master: PleskServerDomain | None,
    target_zone_master: PleskServerDomain,
    domain: DomainName,
    ip: IPv4Address,
) -> None:
    user_action = SetZoneMasterLog(
        user_id=user.id,
        current_zone_master=str(current_zone_master),
        target_zone_master=target_zone_master.name,
        domain=domain.name,
        ip=ip,
    )
    session.add(user_action)
    session.commit()


async def db_log_plesk_login_link_get(
    session: Session,
    user: UserPublic,
    plesk_server: str,
    subscription_id: int,
    subscription_name:str,
    requiest_ip: IPv4Address,
) -> None:
    user_action = GetPleskLoginLinkLog(
        user_id=user.id,
        plesk_server=plesk_server,
        subscription_id=subscription_id,
        subscription_name=subscription_name,
        ssh_username=user.ssh_username,
        ip=requiest_ip,
    )
    session.add(user_action)
    session.commit()


async def get_user_log_entries_by_id(
    session: Session, filters: UserLogFilterSchema, page: int = 1, page_size: int = 10
) -> PaginatedUserLogListSchema | None:
    polymorphic_log = with_polymorphic(UsersActivityLog, "*")
    conditions = []

    for filter, value in filters.model_dump(exclude_none=True).items():
        for subclass in UsersActivityLog.__subclasses__():
            mapper = inspect(subclass)
            if filter in {column.key for column in mapper.column_attrs}:
                subclass_entity = getattr(polymorphic_log, subclass.__name__)
                conditions.append(getattr(subclass_entity, filter) == value)
    query = select(polymorphic_log, User).join(User, polymorphic_log.user_id == User.id)
    query = query.where(and_(*conditions))

    count_query = select(func.count()).select_from(query.subquery())
    total_count = session.execute(count_query).scalar()
    if not total_count:
        return None

    query = query.limit(page_size).offset((page - 1) * page_size)
    actions = session.execute(query).all()
    results = [
        jsonable_encoder({**user.__dict__, "details": {**log_details.__dict__}})
        for log_details, user in actions
    ]

    return PaginatedUserLogListSchema(
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=(total_count + page_size - 1) // page_size,
        data=results,
    )


async def db_log_plesk_mail_test_get(
    session: Session,
    user: UserPublic,
    ip: IPv4Address,
    plesk_server: PleskServerDomain,
    domain: DomainName,
    new_email_created: bool,
) -> None:
    user_action = PleskMailGetTestMailLog(
        user_id=user.id,
        ip=ip,
        plesk_server=plesk_server.name,
        domain=domain.name,
        new_email_created=new_email_created,
    )
    session.add(user_action)
    session.commit()
