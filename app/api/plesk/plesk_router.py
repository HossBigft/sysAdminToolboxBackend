from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Depends,
    BackgroundTasks,
    Request,
    Response,
)
from typing import Annotated

from app.api.plesk.ssh_utils import (
    plesk_fetch_subscription_info,
)
from app.api.plesk.plesk_schemas import (
    SubscriptionListResponseModel,
    SubscriptionDetailsModel,
    SubscriptionLoginLinkInput,
    SetZonemasterInput,
    TestMailCredentials,
    TestMailData,
)
from app.schemas import (
    UserRoles,
    Message,
    SubscriptionName,
    DomainName,
    PleskServerDomain,
    IPv4Address,
    LinuxUsername,
    ValidatedDomainName,
    ValidatedPleskServerDomain,
)
from app.api.plesk.ssh_utils import (
    plesk_generate_subscription_login_link,
)
from app.api.dependencies import CurrentUser, SessionDep, RoleChecker
from app.api.plesk.ssh_utils import (
    is_domain_exist_on_server,
    restart_dns_service_for_domain,
    plesk_get_testmail_login_data,
    get_public_key,
    sign,
)
from app.api.dns.ssh_utils import (
    dns_remove_domain_zone_master,
    dns_get_domain_zone_master,
)
from app.db.crud import (
    log_dns_zone_master_set,
    log_db_plesk_login_link_get,
    log_plesk_mail_test_get,
)
from app.logger import log_plesk_login_link_get
router = APIRouter(tags=["plesk"], prefix="/plesk")


@router.get("/get/subscription/", response_model=SubscriptionListResponseModel)
async def find_plesk_subscription_by_domain(
    domain: Annotated[
        DomainName,
        Query(),
    ],
) -> SubscriptionListResponseModel:
    subscriptions = await plesk_fetch_subscription_info(domain)
    if not subscriptions:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with domain [{domain.name}] not found.",
        )
    subscription_models = [
        SubscriptionDetailsModel.model_validate(sub)
        for sub in subscriptions
    ]

    return SubscriptionListResponseModel(root=subscription_models)


@router.post(
    "/subscription/login-link",
    dependencies=[Depends(RoleChecker([UserRoles.SUPERUSER, UserRoles.ADMIN]))],
)
async def get_subscription_login_link(
    data: SubscriptionLoginLinkInput,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    request: Request,
):
    if not current_user.ssh_username:
        raise HTTPException(
            status_code=404,
            detail="User have no Plesk SSH username",
        )
    login_link = await plesk_generate_subscription_login_link(
        PleskServerDomain(name=data.host),
        data.subscription_id,
        LinuxUsername(current_user.ssh_username),
    )
    request_ip = IPv4Address(ip=request.client.host)
    background_tasks.add_task(
        log_db_plesk_login_link_get,
        session=session,
        user=current_user,
        plesk_server=PleskServerDomain(name=data.host),
        subscription_id=data.subscription_id,
        ip=request_ip,
    )
    background_tasks.add_task(
        log_plesk_login_link_get,
        user=current_user,
        plesk_server=PleskServerDomain(name=data.host),
        subscription_id=data.subscription_id,
        ip=request_ip,
    )

    return login_link


@router.post(
    "/zonemaster/set",
    dependencies=[Depends(RoleChecker([UserRoles.SUPERUSER, UserRoles.ADMIN]))],
)
async def set_zonemaster(
    data: SetZonemasterInput,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    request: Request,
) -> Message:
    curr_zone_master: PleskServerDomain | str | None
    if await is_domain_exist_on_server(
        host=PleskServerDomain(name=data.target_plesk_server),
        domain=SubscriptionName(name=data.domain),
    ):
        curr_zone_master = await dns_get_domain_zone_master(
            SubscriptionName(name=data.domain)
        )

        await dns_remove_domain_zone_master(SubscriptionName(name=data.domain))
        await restart_dns_service_for_domain(
            host=PleskServerDomain(name=data.target_plesk_server),
            domain=SubscriptionName(name=data.domain),
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with domain [{data.domain}] not found.",
        )
    request_ip = IPv4Address(ip=request.client.host)
    background_tasks.add_task(
        log_dns_zone_master_set,
        session=session,
        user=current_user,
        current_zone_master=curr_zone_master,
        target_zone_master=PleskServerDomain(name=data.target_plesk_server),
        domain=DomainName(name=data.domain),
        ip=request_ip,
    )
    return Message(message="Zone master set successfully")


@router.get(
    "/subscription/testmail",
    dependencies=[Depends(RoleChecker([UserRoles.SUPERUSER, UserRoles.ADMIN]))],
    response_model=TestMailCredentials,
)
async def create_testmail_for_domain(
    maildomain: Annotated[ValidatedDomainName, Query()],
    server: Annotated[ValidatedPleskServerDomain, Query()],
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    request: Request,
) -> TestMailCredentials:
    mail_host = PleskServerDomain(name=server)
    mail_domain = SubscriptionName(name=maildomain)

    if await is_domain_exist_on_server(
        host=mail_host,
        domain=mail_domain,
    ):
        data: TestMailData = await plesk_get_testmail_login_data(
            mail_host, mail_domain=mail_domain
        )

    else:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with domain [{mail_domain.name}] not found.",
        )
    request_ip = IPv4Address(ip=request.client.host)
    background_tasks.add_task(
        log_plesk_mail_test_get,
        session=session,
        ip=request_ip,
        user=current_user,
        plesk_server=mail_host,
        domain=DomainName(name=maildomain),
        new_email_created=data.new_email_created,
    )

    return TestMailCredentials.model_validate(data)


@router.get(
    "/publickey",
)
async def share_public_key():
    return Response(content=await get_public_key(), media_type="text/plain")


@router.get(
    "/token",
)
async def get_token(command: str):
    return await sign(command)
