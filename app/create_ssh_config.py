import os
from app.core.config import settings


SSH_SOCKETS_LIVETIME_MIN = 5
GLOBAL_SETTINGS = f"""Host *
	ControlMaster auto
        ControlPath /tmp/\\%r@%h:%p
        ServerAliveInterval 11
        ControlPersist {SSH_SOCKETS_LIVETIME_MIN}m 
        ConnectTimeout=5
        StrictHostKeyChecking no
        UserKnownHostsFile /dev/null
        PasswordAuthentication=no """


def generate_ssh_hosts(servers, ssh_user):
    """
    Generates SSH host configurations as a string.

    :param plesk_servers: Dictionary of hosts and their IPs.
    :param ssh_user: SSH user to be used.
    :return: A string containing the SSH config for all hosts.
    """
    ssh_config = ""
    for host, ips in servers.items():
        for ip in ips:
            ssh_config += f"""
Host {host}.
    HostName {ip}
    User {ssh_user}
"""
    return ssh_config

def main() -> None:
    config = "/root/ssh_config/config"
    os.makedirs(os.path.dirname(config), exist_ok=True)
    with open(config, "w") as f:
        f.write(GLOBAL_SETTINGS)
        f.write(generate_ssh_hosts(settings.DNS_SLAVE_SERVERS, "root"))
        f.write(generate_ssh_hosts(settings.PLESK_SERVERS, settings.SSH_USER))

if __name__ == "__main__":
    main()
