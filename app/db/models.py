import uuid

from sqlalchemy import ForeignKey, String, UUID, Boolean, Enum, DateTime, func
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from datetime import datetime

from app.schemas import UserRoles, UserActionType


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    role: Mapped[Enum] = mapped_column(
        Enum(UserRoles), default=UserRoles.USER, nullable=False
    )
    ssh_username: Mapped[str] = mapped_column(String(32), nullable=True)
    is_active: Mapped[Boolean] = mapped_column(Boolean, default=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)


class UsersActivityLog(Base):
    __tablename__ = "users_activity_log"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    log_type: Mapped[UserActionType] = mapped_column(
        Enum(UserActionType), nullable=False
    )

    __mapper_args__ = {
        "polymorphic_identity": "activity_log",
        "polymorphic_on": "log_type",
    }


class DeleteZonemasterLog(UsersActivityLog):
    __tablename__ = "zone_master_delete_log"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users_activity_log.id", ondelete="CASCADE"),
        primary_key=True,
    )
    domain: Mapped[str] = mapped_column(String, nullable=False)
    current_zone_master: Mapped[str] = mapped_column(String, nullable=False)

    __mapper_args__ = {"polymorphic_identity": UserActionType.DELETE_ZONE_MASTER}


class SetZoneMasterLog(UsersActivityLog):
    __tablename__ = "zone_master_set_log"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users_activity_log.id", ondelete="CASCADE"),
        primary_key=True,
    )
    current_zone_master: Mapped[str | None] = mapped_column(String, nullable=True)
    target_zone_master: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)

    __mapper_args__ = {"polymorphic_identity": UserActionType.SET_ZONE_MASTER}


class GetZoneMasterLog(UsersActivityLog):
    __tablename__ = "zone_master_get_log"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users_activity_log.id", ondelete="CASCADE"),
        primary_key=True,
    )
    domain: Mapped[str] = mapped_column(String, nullable=False)

    __mapper_args__ = {"polymorphic_identity": UserActionType.GET_ZONE_MASTER}


class GetPleskLoginLinkLog(UsersActivityLog):
    __tablename__ = "plesk_get_subscription_login_link_log"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users_activity_log.id", ondelete="CASCADE"),
        primary_key=True,
    )
    plesk_server: Mapped[str] = mapped_column(String, nullable=False)
    ssh_username: Mapped[str] = mapped_column(String, nullable=False)
    subscription_id: Mapped[str] = mapped_column(String, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": UserActionType.GET_SUBSCRIPTION_LOGIN_LINK
    }
