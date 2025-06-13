from app.plesk.plesk_service import PleskService
from app.schemas import (DomainName)
async def main():
    print("Running requests on cold connections")
    await PleskService().fetch_subscription_info(DomainName(name="gruzo.kz"))
    
    print("Running requests on warmed connections")
    await PleskService().fetch_subscription_info(DomainName(name="gruzo.kz"))