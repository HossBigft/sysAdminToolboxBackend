import logging
import os
import shutil
import gzip

from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from starlette.middleware.base import BaseHTTPMiddleware

from typing import List


from sqlalchemy.orm import Session
from fastapi import Request
from app.db.crud import (
    db_log_plesk_login_link_get,
    db_log_dns_zone_master_set,
    db_log_plesk_mail_test_get,
    db_log_dns_zonemaster_removal,
    db_log_dns_zonemaster_fetch,
)
from app.dns.dns_models import ZoneMaster
from app.schemas import (
    UserActionType,
    PleskServerDomain,
    IPv4Address,
    SubscriptionName,
    UserPublic,
    DomainName,
)

from app.core.config import settings


USER_ACTION_LOG_SIZE_MB = 10


def round_up_seconds(dt: datetime):
    if dt.microsecond > 0:
        return (dt + timedelta(seconds=1)).replace(microsecond=0)
    return dt.replace(microsecond=0)


def _get_timestamp() -> str:
    now = datetime.now()
    rounded_time = round_up_seconds(now)
    return rounded_time.isoformat()


class CompactDockerFormatter(logging.Formatter):
    def format(self, record):
        timestamp = _get_timestamp()

        message = record.getMessage()
        client = "-"
        request_line = "-"
        status_code = "-"
        duration_ms = getattr(record, "duration_ms", None)

        try:
            parts = message.split(" - ")
            client = parts[0]
            request_info = parts[1].strip("'")
            request_line, status_code = request_info.rsplit(" ", 1)
        except Exception:
            pass

        time_str = f"{duration_ms:.2f}ms" if duration_ms is not None else "-"

        return (
            f"{timestamp} level={record.levelname} "
            f'client={client} status={status_code} req="{request_line}" time={time_str}'
        )


def disable_default_uvicorn_access_logs():
    logger = logging.getLogger("uvicorn.access")
    logger.handlers.clear()


def setup_custom_access_logger():
    logger = logging.getLogger("app.access")
    handler = logging.StreamHandler()
    logger.propagate = False
    handler.setFormatter(CompactDockerFormatter())
    logger.addHandler(handler)
    return logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        real_ip = _get_request_ip(request)

        start = datetime.now()
        response = await call_next(request)
        duration = (datetime.now() - start).total_seconds() * 1000  # in ms

        request_line = f"{request.method} {request.url.path} HTTP/{request.scope.get('http_version', '1.1')}"
        logger = logging.getLogger("app.access")
        logger.info(
            f"{real_ip} - '{request_line} {response.status_code}'",
            extra={"duration_ms": duration},
        )

        return response


def _mb_to_bytes(mb: int) -> int:
    return mb * 1024 * 1024


def setup_actions_logger():
    def _namer(name):
        return name + ".gz"

    def _compressed_rotator(source, dest):
        with open(source, "rb") as f_in:
            with gzip.open(dest, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(source)

    user_action_logger = logging.getLogger("app.user_actions")
    user_action_logger.setLevel(logging.INFO)

    log_directory = "/var/log/backend_app"
    os.makedirs(log_directory, exist_ok=True)

    file_handler = RotatingFileHandler(
        os.path.join(log_directory, "user_action.log"),
        mode="a",
        maxBytes=_mb_to_bytes(USER_ACTION_LOG_SIZE_MB),
        backupCount=5,
    )

    file_handler.rotator = _compressed_rotator
    file_handler.namer = _namer
    user_action_logger.addHandler(file_handler)


class LogEntry:
    def __init__(self, action: UserActionType, user: UserPublic, request_ip: str):
        self.fields = {}
        self.field("action_type", action.value)
        self.field("backend_user", user.email)
        self.field("backend_user_id", user.id)
        self.field("ip", request_ip)

    def __str__(self) -> str:
        fields_str: List[str] = []

        for key, val in self.fields.items():
            fields_str.append(f"{key}: {val}")
        return f"{_get_timestamp()} | " + " | ".join(fields_str)

    def field(self, name, value):
        self.fields[name] = value
        return self


def _get_request_ip(request: Request) -> str:
    ip: str
    try:
        ip = request.headers["X-Forwarded-For"]
    except KeyError:
        ip = request.client.host
    return ip


def get_user_action_logger():
    return logging.getLogger("app.user_actions")


async def log_plesk_login_link_get(
    user: UserPublic,
    plesk_server: str,
    subscription_id: int,
    subscription_name: str,
    request: Request,
    session: Session,
):
    request_ip = IPv4Address.model_validate(_get_request_ip(request))

    log_entry = LogEntry(
        UserActionType.GET_SUBSCRIPTION_LOGIN_LINK_BY_DOMAIN, user, str(request_ip)
    )

    log_entry.field("plesk_user", user.ssh_username)
    log_entry.field("plesk_server", plesk_server)
    log_entry.field("subscription_name", subscription_name)
    log_entry.field("subscription_id", subscription_id)
    get_user_action_logger().info(str(log_entry))
    await db_log_plesk_login_link_get(
        session=session,
        user=user,
        plesk_server=plesk_server,
        subscription_id=subscription_id,
        subscription_name=subscription_name,
        requiest_ip=request_ip,
    )




async def log_dns_zone_master_set(
    domain: DomainName,
    current_zonemasters: List[ZoneMaster],
    target_zone_master: PleskServerDomain,
    session: Session,
    user: UserPublic,
    request: Request,
):
    request_ip = IPv4Address.model_validate(_get_request_ip(request))

    current_zonemasters_json = (
        ", ".join([zonemaster.model_dump_json() for zonemaster in current_zonemasters]),
    )
    
    
    log_entry = LogEntry(UserActionType.SET_ZONE_MASTER, user, str(request_ip))
    log_entry.field("domain", domain)
    log_entry.field("current_zone_masters", current_zonemasters_json)
    log_entry.field("target_zone_master", target_zone_master.name)

    get_user_action_logger().info(str(log_entry))
    
    await db_log_dns_zone_master_set(
        session=session,
        user=user,
        current_zone_master=", ".join(current_zonemasters_json),
        target_zone_master=target_zone_master,
        ip=request_ip,
        domain=domain,
    )



async def log_plesk_mail_test_get(
    plesk_mail_server: PleskServerDomain,
    mail_domain: DomainName,
    is_new_email_created: bool,
    session: Session,
    user: UserPublic,
    request: Request,
):
    request_ip = IPv4Address.model_validate(_get_request_ip(request))
    log_entry = LogEntry(
        UserActionType.GET_TEST_MAIL_CREDENTIALS, user, str(request_ip)
    )
    log_entry.field("backend_user", user.email)
    log_entry.field("mail_domain", mail_domain)
    log_entry.field("is_new_mail_created", is_new_email_created)
    log_entry.field("plesk_mail_server", plesk_mail_server)

    get_user_action_logger().info(str(log_entry))
    
    await db_log_plesk_mail_test_get(
        session=session,
        ip=request_ip,
        user=user,
        plesk_server=plesk_mail_server,
        domain=mail_domain,
        new_email_created=is_new_email_created,
    )



async def log_dns_remove_zone(
    domain: DomainName,
    current_zonemaster: str,
    user: UserPublic,
    session: Session,
    request: Request,
):
    request_ip = IPv4Address.model_validate(_get_request_ip(request))

    log_entry = LogEntry(UserActionType.DELETE_ZONE_MASTER, user, str(request_ip))
    log_entry.field("domain", domain)
    log_entry.field("current_zone_master", current_zonemaster)
    get_user_action_logger().info(str(log_entry))
    
    await db_log_dns_zonemaster_removal(
        session=session,
        user=user,
        current_zone_master=current_zonemaster,
        domain=domain,
        ip=request_ip,
    )



async def log_dns_get_zonemaster(
    domain: SubscriptionName, user: UserPublic, session: Session, request: Request
):
    request_ip = IPv4Address.model_validate(_get_request_ip(request))

    log_entry = LogEntry(UserActionType.GET_ZONE_MASTER, user, str(request_ip))
    log_entry.field("domain", domain)
    get_user_action_logger().info(str(log_entry))
    
    await db_log_dns_zonemaster_fetch(
        session=session, user=user, domain=domain, ip=request_ip
    )




def setup_ssh_logger():
    ssh_logger = logging.getLogger("app.ssh_operations")
    if settings.ENVIRONMENT == "local":
        ssh_logger.setLevel(logging.DEBUG)
    else:
        ssh_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    ssh_logger.addHandler(handler)
    ssh_logger.propagate = False
    
    asyncssh_logger = logging.getLogger("asyncssh")
    asyncssh_logger.setLevel(logging.CRITICAL)     
    asyncssh_logger.propagate = False   
               
    return ssh_logger


def get_ssh_logger():
    return logging.getLogger("app.ssh_operations")


def log_ssh_request(host: str, command: str):

    logger = get_ssh_logger()
    if settings.ENVIRONMENT == "local":
        logger.debug(f"{host} executes \"{command}\" | Awaiting result...")
    else:
        logger.info(f"{host} executing '{command}' | Awaiting result...")



def log_ssh_response(response, execution_time: float):
    logger = get_ssh_logger()
    if settings.ENVIRONMENT == "local":
        response_info = response.model_dump_json(indent=1)
        logger.info(
            f"{response.host} answered {response.status} ({execution_time:.2f}s): "
            f"{response_info}"
        )
    else:
        response_info = f'{{"status": "{response.status}", "code": {response.code}, "message": "{response.message}"}}'
        logger.info(
            f"{response.host} answered {response.status} ({execution_time:.2f}s): "
            f"{response_info}"
        )
