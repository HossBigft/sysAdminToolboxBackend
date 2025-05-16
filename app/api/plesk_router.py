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

from app.plesk.plesk_schemas import (
    SubscriptionListResponseModel,
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
from app.api.dependencies import CurrentUser, SessionDep, RoleChecker

from app.db.crud import (
    log_dns_zone_master_set,
    log_db_plesk_login_link_get,
    log_plesk_mail_test_get,
)
from app.core_utils.logger import log_plesk_login_link_get
from app.api.dependencies import get_token_signer
from app.plesk.plesk_service import PleskService
from app.dns.dns_service import DNSService

_token_signer = get_token_signer()
router = APIRouter(tags=["plesk"], prefix="/plesk")


@router.get("/get/subscription/", response_model=SubscriptionListResponseModel)
async def find_plesk_subscription_by_domain(
        domain: Annotated[DomainName, Query()],
) -> SubscriptionListResponseModel:
    subscriptions = await PleskService().fetch_subscription_info(domain)
    return SubscriptionListResponseModel(root=subscriptions)


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
    login_link = await PleskService().generate_subscription_login_link(
        PleskServerDomain(name=data.host),
        data.subscription_id,
        LinuxUsername(current_user.ssh_username),
    )
    if not login_link:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with {data.subscription_id} ID doesn't exist.",
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
    if await PleskService().is_domain_exist_on_server(
            host=PleskServerDomain(name=data.target_plesk_server),
            domain=SubscriptionName(name=data.domain),
    ):
        curr_zone_master = await DNSService().get_zone_masters(
            DomainName(name=data.domain)
        )

        await DNSService().remove_zone(DomainName(name=data.domain))
        await PleskService().restart_dns_service_for_domain(
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

    data: TestMailData = await PleskService().get_testmail_login_data(
        mail_host, mail_domain=mail_domain
    )

    if not data:
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
    return Response(
        content=_token_signer.get_public_key_base64(), media_type="text/plain"
    )


@router.get(
    "/token",
)
async def get_token(command: str):
    return _token_signer.create_signed_token(command)
