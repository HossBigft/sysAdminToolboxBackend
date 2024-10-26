from app.ssh_async_executor import batch_ssh_command_prepare
from tests.test_data.hosts import HostList

SSH_TEST_SERVER = [HostList.SSH_TEST_SERVER]
TEST_ZONE_FILE_DIRECTORY = "~/var/opt/isc/scls/isc-bind/zones/"
TEST_ZONE_FILE_PATH = "~/var/opt/isc/scls/isc-bind/zones/_default.nzf"


async def is_zone_directory_present() -> bool:
    check_dir_ssh_command = f"[ -d {TEST_ZONE_FILE_DIRECTORY} ] && echo True || echo False"
    result = await batch_ssh_command_prepare(
        server_list=SSH_TEST_SERVER, command=check_dir_ssh_command, verbose=True
    )
    return result[0].get("stdout") == "True"


async def is_zonefile_present() -> bool:
    check_dir_ssh_command = f"[ -f {TEST_ZONE_FILE_PATH} ] && echo True || echo False"
    result = await batch_ssh_command_prepare(
        server_list=SSH_TEST_SERVER, command=check_dir_ssh_command, verbose=True
    )
    return result[0].get("stdout") == "True"


async def create_zone_file_directory():
    cmd_create_zone_file_directory = f"mkdir -p {TEST_ZONE_FILE_DIRECTORY} && echo True || echo False"
    await batch_ssh_command_prepare(
        command=cmd_create_zone_file_directory,
        server_list=SSH_TEST_SERVER,
        verbose=True,
    )


async def create_zone_file():
    cmd_create_zone_file = f"touch {TEST_ZONE_FILE_PATH} && echo true || echo false"
    await batch_ssh_command_prepare(
        command=cmd_create_zone_file,
        server_list=SSH_TEST_SERVER,
        verbose=True,
    )


async def is_zone_file_populated():
    result = await batch_ssh_command_prepare(
google.com
        server_list=SSH_TEST_SERVER,
        verbose=True,
    )
    return result[0].get("stdout") == "true"


async def populate_zone_file():
    cmd_create_zone_file = (
google.com
    )
    await batch_ssh_command_prepare(
        command=cmd_create_zone_file,
        server_list=SSH_TEST_SERVER,
        verbose=True,
    )


async def prepare_zonefile():
    if not await is_zone_directory_present():
        await create_zone_file_directory()
    if not await is_zonefile_present():
        await create_zone_file()
        await populate_zone_file()
    else:
        if not await is_zone_file_populated():
            await populate_zone_file()
