import logging
import os
import shutil
import gzip

from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from typing import List

from exceptiongroup import catch
from sqlalchemy.orm import Session
from fastapi import (
    Request
)
from app.db.crud import db_log_plesk_login_link_get
from app.schemas import UserActionType, PleskServerDomain, IPv4Address, SubscriptionName

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
        level = record.levelname

        try:

            client = record.args.get("client", "-")
            status = record.args.get("status_code", "-")
            request_line = record.args.get("request_line", "-")
            response_time = record.args.get("response_time", "-")

            return f'{timestamp} level={level} client={client} status={status} req="{request_line}" time={response_time}ms'
        except:
            return f'{timestamp} level={level} msg="{record.getMessage()}"'


def setup_uvicorn_logger():
    logger = logging.getLogger("uvicorn.access")
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(CompactDockerFormatter())
    logger.addHandler(handler)
    return logger


def _mb_to_bytes(mb: int) -> int:
    return mb * 1024 * 1024


def setup_actions_logger():
    def _namer(name):
        return name + ".gz"

    def _compressed_rotator(source, dest):
        with open(source, 'rb') as f_in:
            with gzip.open(dest, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(source)

    user_action_logger = logging.getLogger("app.user_actions")
    user_action_logger.setLevel(logging.INFO)

    log_directory = '/var/log/backend_app'
    os.makedirs(log_directory, exist_ok=True)

    file_handler = RotatingFileHandler(os.path.join(log_directory, 'user_action.log'), mode='a',
                                       maxBytes=_mb_to_bytes(USER_ACTION_LOG_SIZE_MB), backupCount=5)

    file_handler.rotator = _compressed_rotator
    file_handler.namer = _namer
    user_action_logger.addHandler(file_handler)


class LogEntry():
    def __init__(self, action: UserActionType):
        self.fields = {}
        self.field("action_type", action.value)

    def __str__(self) -> str:
        fields_str: List[str] = []

        for key, val in self.fields.items():
            fields_str.append(f"{key}: {val}")
        return f"{_get_timestamp()} | " + " | ".join(fields_str)

    def field(self, name, value):
        self.fields[name] = value
        return self

    def str(self) -> str:
        return str(self)


def _get_request_ip(request: Request) -> str:
    ip:str
    try:
        ip=request.headers["X-Forwarded-For"]
    except KeyError:
        ip=request.client.host
    return ip


async def log_plesk_login_link_get(
        user,
        plesk_server: str,
        subscription_id: int,
        subscription_name: str,
        request: Request,
        session: Session,
):
    app_logger = logging.getLogger("app.user_actions")
    request_ip = IPv4Address.model_validate(_get_request_ip(request))

    log_message = LogEntry(UserActionType.GET_SUBSCRIPTION_LOGIN_LINK_BY_DOMAIN).field("plesk_user",
                                                                                       user.ssh_username).field(
        "backend_user",
        user.email).field(
        "plesk_server",
        plesk_server).field(
        "subscription_name", subscription_name).field("subscription_id", subscription_id).field("IP", request_ip)

    await db_log_plesk_login_link_get(session=session,
                                      user=user,
                                      plesk_server=plesk_server,
                                      subscription_id=subscription_id,
                                      subscription_name=subscription_name,
                                      requiest_ip=request_ip)
    app_logger.info(log_message.str())
