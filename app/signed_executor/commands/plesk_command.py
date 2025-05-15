from app.signed_executor.commands.signed_command import SignedCommand

class PleskCommand(SignedCommand):
    """Commands for Plesk operations."""
    
    def __init__(self, operation: str):
        super().__init__("PLESK", operation)
    
    @classmethod
    def get_login_link(cls) -> "PleskCommand":
        return cls("GET_LOGIN_LINK")
    
    @classmethod
    def fetch_subscription_info(cls) -> "PleskCommand":
        return cls("FETCH_SUBSCRIPTION_INFO")
    
    @classmethod
    def get_testmail_credentials(cls) -> "PleskCommand":
        return cls("GET_TESTMAIL_CREDENTIALS")
    
    @classmethod
    def restart_dns_service(cls) -> "PleskCommand":
        return cls("RESTART_DNS_SERVICE")
    
    @classmethod
    def get_subscription_id_by_domain(cls) -> "PleskCommand":
        return cls("GET_SUBSCRIPTION_ID_BY_DOMAIN")
