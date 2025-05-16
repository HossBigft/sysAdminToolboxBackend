import logging
from datetime import datetime, timedelta
from app.schemas import UserActionType


def round_up_seconds(dt):
    if dt.microsecond > 0:
        return (dt + timedelta(seconds=1)).replace(microsecond=0)
    return dt.replace(microsecond=0)


class CompactDockerFormatter(logging.Formatter):
    def format(self, record):
        now = datetime.now()
        rounded_time = round_up_seconds(now)
        timestamp = rounded_time.isoformat()
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


def setup_actios_logger():
    app_logger = logging.getLogger("app.user_actions")
    app_logger.setLevel(logging.INFO)


def log_plesk_login_link_get(
        user,
        plesk_server: str,
        subscription_id: int,
        ip: str,
):
    app_logger = logging.getLogger("app.user_actions")
    log_message = (
        f"{UserActionType.GET_SUBSCRIPTION_LOGIN_LINK} | User: {user.email} | Server: {plesk_server} | "
        f"Subscription: {subscription_id} | IP: {ip}"
    )

    app_logger.info(log_message)
