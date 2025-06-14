import asyncio

from app.core_utils.loggers import setup_ssh_logger
from app.plesk.plesk_service import PleskService
from app.schemas import SubscriptionName




async def main():
    setup_ssh_logger()
    print("Running requests on cold connections")
    await PleskService().fetch_subscription_info(SubscriptionName(name="gruzo.kz"))
    
    print("Running requests on warmed connections")
    await PleskService().fetch_subscription_info(SubscriptionName(name="gruzo.kz"))

if __name__ == "__main__":
    asyncio.run(main())