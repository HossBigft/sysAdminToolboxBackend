import json

from typing import List
from fastapi import HTTPException


from app.core.AsyncSSHandler import execute_ssh_command, execute_ssh_commands_in_batch
from app.api.dependencies import get_token_signer

from app.schemas import PleskServerDomain, LinuxUsername, PLESK_SERVER_LIST, OperationResult, ExecutionStatus, DomainName
from app.api.plesk.plesk_schemas import (
    SubscriptionName,
    TestMailData,
    SubscriptionDetailsModel
)
from app.core.DomainMapper import HOSTS

_token_signer = get_token_signer()


async def fetch_subscription_id_by_domain(
        host: PleskServerDomain, domain: SubscriptionName
) -> dict | None:
    result = await execute_ssh_command(host.name, command="execute " + _token_signer.create_signed_token(
        f"PLESK.GET_SUBSCRIPTION_ID_BY_DOMAIN {domain.name}"))

    if result["stdout"]:
        id_list = json.loads(result["stdout"])
        return id_list
    else:
        return None


async def is_domain_exist_on_server(
        host: PleskServerDomain, domain: SubscriptionName
) -> bool:
    return await fetch_subscription_id_by_domain(host=host, domain=domain) is not None


async def restart_dns_service_for_domain(
        host: PleskServerDomain, domain: SubscriptionName
) -> None:
    await execute_ssh_command(
        host=host.name,
        command="execute "
                + _token_signer.create_signed_token(f"PLESK.RESTART_DNS_SERVICE {domain.name}"),
        verbose=True,
    )


async def batch_ssh_execute(cmd: str):
    return await execute_ssh_commands_in_batch(
        server_list=PLESK_SERVER_LIST,
        command=cmd,
        verbose=True,
    )


async def plesk_fetch_subscription_info(
        domain: DomainName,
) -> List[SubscriptionDetailsModel]:
    lowercase_domain_name = domain.name.lower()
    ssh_command = _token_signer.create_signed_token(
        f"PLESK.FETCH_SUBSCRIPTION_INFO {lowercase_domain_name}"
    )
    answers = await batch_ssh_execute("execute " + ssh_command)

    results = []
    for answer in answers:
        raw = answer.get("stdout")
        hostName = answer.get("host")

        if not raw or not hostName:
            continue
        answerJson = json.loads(raw)
        op_result = OperationResult.model_validate(answerJson)

        if op_result.status == ExecutionStatus.OK and op_result.payload:
            for item in op_result.payload:
                model_data = {
                    "host": HOSTS.resolve_domain(hostName),
                    **item
                }
                model = SubscriptionDetailsModel.model_validate(model_data)
                results.append(model)

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No subscription information found for domain: {domain.name}"
        )

    return results


async def plesk_generate_subscription_login_link(
        host: PleskServerDomain, subscription_id: int, ssh_username: LinuxUsername
) -> str | None:
    result = await execute_ssh_command(
        host=host.name,
        command="execute "
                + _token_signer.create_signed_token(
            f"PLESK.GET_LOGIN_LINK {subscription_id} {ssh_username}"
        ),
    )
    subscription_login_link = result["stdout"]
    if not subscription_login_link:
        return None
    return subscription_login_link


async def plesk_get_testmail_login_data(
        host: PleskServerDomain, mail_domain: SubscriptionName
) -> TestMailData | None:
    result = await execute_ssh_command(
        host=host.name,
        command="execute "
                + _token_signer.create_signed_token(
            f"PLESK.GET_TESTMAIL_CREDENTIALS {mail_domain.name}"
        ),
    )

    if result["stdout"]:
        data_dict = json.loads(result["stdout"])
        return TestMailData.model_validate(data_dict)
    else:
        return None
