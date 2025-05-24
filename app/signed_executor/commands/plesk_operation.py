from app.signed_executor.commands.signed_operation import SignedOperation

class PleskOperation(SignedOperation):
    """Commands for Plesk operations."""
    
    def __init__(self, operation: str):
        super().__init__("PLESK", operation)
    
    @classmethod
    def get_login_link(cls) -> "PleskOperation":
        return cls("GET_LOGIN_LINK")
    
    @classmethod
    def fetch_subscription_info(cls) -> "PleskOperation":
        return cls("FETCH_SUBSCRIPTION_INFO")
    
    @classmethod
    def get_testmail_credentials(cls) -> "PleskOperation":
        return cls("GET_TESTMAIL_CREDENTIALS")
    
    @classmethod
    def restart_dns_service(cls) -> "PleskOperation":
        return cls("RESTART_DNS_SERVICE")
    
    @classmethod
    def get_subscription_id_by_domain(cls) -> "PleskOperation":
        return cls("GET_SUBSCRIPTION_ID_BY_DOMAIN")
