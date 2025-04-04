from app.core.config import settings
from app.schemas import HostIpData, IPv4Address, ValidatedDomainName


class DomainMapper:
    def __init__(self, hosts_data: dict[ValidatedDomainName, list[IPv4Address]]):
        """
        Initialize the mapper with host data.

        Args:
            hosts_data: dictionary mapping domain names to IP address(es)
        """
        self.domain_to_ips = {}
        self.ip_to_domains: dict[str, str] = {}

        # Populate the mappings
        self.update_mappings(hosts_data)

    def update_mappings(self, hosts_data: dict[ValidatedDomainName, list[IPv4Address]]):
        """
        Update the internal mappings with new host data.

        Args:
            hosts_data: dictionary mapping domain names to IP address(es)
        """
        for domain, ips in hosts_data.items():
            # Handle both single IP (string) and multiple IPs (list)
            if isinstance(ips, str):
                ips = [ips]

            # Update domain -> IPs mapping
            self.domain_to_ips[domain] = ips

            # Update IP -> domains mapping
            for ip in ips:
                self.ip_to_domains[str(ip)] = domain

    def resolve_domain(self, domain: ValidatedDomainName) -> HostIpData | None:
        """
        Get all IP addresses for a given domain.

        Args:
            domain: The domain name to look up

        Returns:
            List of IP addresses for the domain
        """
        resolved_ips = self.domain_to_ips.get(domain, None)
        if not resolved_ips:
            return None
        return HostIpData(domain=domain, ips=resolved_ips)

    def resolve_ip(self, ip: IPv4Address) -> HostIpData | None:
        """
        Get all domains associated with a given IP.

        Args:
            ip: The IP address to look up

        Returns:
            List of domains associated with the IP
        """
        resolved_domain = self.ip_to_domains.get(str(ip.ip), None)
        resolved_ips = self.domain_to_ips.get(resolved_domain, None)
        if not resolved_domain or not resolved_ips:
            return None
        return HostIpData(domain=resolved_domain, ips=resolved_ips)

    def add_mapping(self, domain: ValidatedDomainName, ip: list[IPv4Address]):
        """
        Add a new mapping between domain and IP(s).

        Args:
            domain: The domain name
            ip: IP address or list of IP addresses
        """
        self.update_mappings({domain: ip})

    def remove_domain(self, domain: ValidatedDomainName):
        """
        Remove a domain and all its IP mappings.

        Args:
            domain: The domain to remove
        """
        if domain in self.domain_to_ips:
            ips = self.domain_to_ips[domain]

            for ip in ips:
                ip_str = str(ip)
                if self.ip_to_domains.get(ip_str) == domain:
                    del self.ip_to_domains[ip_str]

            del self.domain_to_ips[domain]

    def remove_ip(self, ip: IPv4Address):
        """
        Remove an IP and all its domain mappings.

        Args:
            ip: The IP address to remove
        """
        ip_str = str(ip)
        if ip in self.ip_to_domains:
            domains = self.ip_to_domains[ip_str]
            # Remove the IP from each domain's mapping
            for domain in domains:
                if ip in self.domain_to_ips.get(domain, []):
                    self.domain_to_ips[domain].remove(ip)
                    # If no IPs left for this domain, remove the domain entry
                    if not self.domain_to_ips[domain]:
                        del self.domain_to_ips[domain]
            # Remove the IP entry
            del self.ip_to_domains[ip_str]


HOSTS = DomainMapper(settings.PLESK_SERVERS)
HOSTS.update_mappings(settings.DNS_SLAVE_SERVERS)
HOSTS.update_mappings(settings.ADDITIONAL_HOSTS)
