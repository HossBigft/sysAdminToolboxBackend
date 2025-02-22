from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import crud
from app.core.config import settings
from app.schemas import UserCreate, UserRoles
from app.db.models import User, Base

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI), echo=False)


def init_db(session: Session) -> None:
    Base.metadata.create_all(engine)

    user = session.execute(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            role=UserRoles.SUPERUSER,
        )
        user = crud.create_user(session=session, user_create=user_in)
