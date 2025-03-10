import uuid

from sqlalchemy import ForeignKey, String, UUID, Boolean, Enum, DateTime, func, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import sqlalchemy.types as types
from datetime import datetime

from app.schemas import UserRoles, UserActionType, IPv4Address


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


class IPv4AddressType(types.TypeDecorator):
    """Custom SQLAlchemy type to store IPv4Address as a string."""

    impl = String(15)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert Python IPv4Address to string before saving to DB."""
        if isinstance(value, IPv4Address):
            return str(value)
        return value  # Assume it's already a string

    def process_result_value(self, value, dialect):
        """Convert string from DB back to Python IPv4Address."""
        if value is not None:
            return IPv4Address(ip=value)
        return value


class UsersActivityLog(Base):
    __tablename__ = "log_user_activity"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    ip: Mapped[IPv4AddressType] = mapped_column(IPv4AddressType, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    log_type: Mapped[UserActionType] = mapped_column(
        Enum(UserActionType), nullable=False
    )

    __mapper_args__ = {
        "polymorphic_identity": "activity_log",
        "polymorphic_on": "log_type",
    }


class DeleteZonemasterLog(UsersActivityLog):
    __tablename__ = "log_zone_master_delete"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("log_user_activity.id", ondelete="CASCADE"),
        primary_key=True,
    )
    domain: Mapped[str] = mapped_column(String, nullable=False)
    current_zone_master: Mapped[str] = mapped_column(String, nullable=False)

    __mapper_args__ = {"polymorphic_identity": UserActionType.DELETE_ZONE_MASTER}


class SetZoneMasterLog(UsersActivityLog):
    __tablename__ = "log_zone_master_set"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("log_user_activity.id", ondelete="CASCADE"),
        primary_key=True,
    )
    current_zone_master: Mapped[str | None] = mapped_column(String, nullable=True)
    target_zone_master: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)

    __mapper_args__ = {"polymorphic_identity": UserActionType.SET_ZONE_MASTER}


class GetZoneMasterLog(UsersActivityLog):
    __tablename__ = "log_zone_master_get"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("log_user_activity.id", ondelete="CASCADE"),
        primary_key=True,
    )
    domain: Mapped[str] = mapped_column(String, nullable=False)

    __mapper_args__ = {"polymorphic_identity": UserActionType.GET_ZONE_MASTER}


class GetPleskLoginLinkLog(UsersActivityLog):
    __tablename__ = "log_plesk_subscription_login"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("log_user_activity.id", ondelete="CASCADE"),
        primary_key=True,
    )
    plesk_server: Mapped[str] = mapped_column(String, nullable=False)
    ssh_username: Mapped[str] = mapped_column(String, nullable=False)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": UserActionType.GET_SUBSCRIPTION_LOGIN_LINK
    }
