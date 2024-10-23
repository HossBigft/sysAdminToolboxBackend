from fastapi import FastAPI, HTTPException, Query, Depends, status
from .dns_resolver import resolve_record, RecordNotFoundError
import uvicorn
from typing import Annotated
from pydantic.networks import IPvAnyAddress
from .ssh_zone_master import getDomainZoneMaster
from .ssh_plesk_subscription_info_retriever import query_domain_info
from .plesk_queries import send_hello
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)


async def validate_domain_name(
    domain: Annotated[
        str, Query(min_length=3, max_length=63, pattern=DOMAIN_REGEX_PATTERN)
    ],
):
    return domain


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/dns/resolve/a/")
async def get_a_record(domain: str = Depends(validate_domain_name)):
    try:
        a_records = resolve_record(domain, "A")
        return {"domain": domain, "records": a_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/dns/resolve/ptr/")
async def get_ptr_record(
    ip: IPvAnyAddress,
):
    try:
        ptr_records = resolve_record(str(ip), "PTR")
        return {"ip": ip, "records": ptr_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/dns/get/zonemaster/")
async def get_zone_master_from_dns_servers(domain: str = Depends(validate_domain_name)):
    try:
        zone_masters_dict = await getDomainZoneMaster(domain)
        return zone_masters_dict
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/plesk/get/subscription/")
async def find_plesk_subscription_by_domain(
    domain: str = Depends(validate_domain_name),
):
    try:
        subscriptions = await query_domain_info(domain)
        return subscriptions
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/dns/resolve/mx/")
async def get_mx_record(domain: str = Depends(validate_domain_name)):
    try:
        mx_records = resolve_record(domain, "MX")
        return {"domain": domain, "records": mx_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/dns/resolve/ns/")
async def get_ns_records(domain: str = Depends(validate_domain_name)):
    try:
        ns_records = resolve_record(domain, "NS")
        return {"domain": domain, "records": ns_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    }
}

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "506a75b7433015d172573416d7f6074f6ab529184e023c06416be7381ab06c8b"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/users/me/", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user


@app.get("/users/me/items/")
async def read_own_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return [{"item_id": "Foo", "owner": current_user.username}]


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", host="IP_PLACEHOLDER", port=5000, log_level="debug", reload=True
    )
