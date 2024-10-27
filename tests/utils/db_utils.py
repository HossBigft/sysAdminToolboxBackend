from sqlmodel import Field, Session, SQLModel, create_engine, text

TEST_DB_NAME = "testdb"


# Define the Client model
class Client(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    pname: str = Field(..., max_length=255)  # Use max_length for VARCHAR
    login: str = Field(..., max_length=255)  # Use max_length for VARCHAR


# Define the Domain model
class Domain(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(..., max_length=255)  # Specify length
    webspace_id: int
    cl_id: int = Field(default=None, foreign_key="client.id")


_user = "vtest"
_password = "Guakufooquaek7Houph0"
_connector = "mariadb+pymysql"
_host = "IP_PLACEHOLDER"


def __create_database(db_name: str):
    mariadb_url = f"{_connector}://{_user}:{_password}@{_host}/"
    engine = create_engine(mariadb_url)
    with engine.connect() as connection:
        statement = text(f"CREATE DATABASE IF NOT EXISTS {db_name};")
        connection.execute(statement)


# Create the tables in the database
def __create_db_and_tables(db_name: str):
    # Update the engine to point to the new database
    db_engine = create_engine(
        f"{_connector}://{_user}:{_password}@{_host}/{db_name}"
    )  # Update with your credentials
    SQLModel.metadata.create_all(db_engine)


def __insert_sample_data(db_name: str):
    db_engine = create_engine(f"{_connector}://{_user}:{_password}@{_host}/{db_name}")
    with Session(db_engine) as session:
        # Create sample clients
        client_a = Client(pname="Client A", login="userA")
        client_b = Client(pname="Client B", login="userB")
        client_c = Client(pname="Client C", login="userC")

        session.add(client_a)
        session.add(client_b)
        session.add(client_c)
        session.commit()

        # Create sample domains
        domain_data = [
            Domain(name="example.com", webspace_id=0, cl_id=client_a.id),
            Domain(name="test.com", webspace_id=1, cl_id=client_a.id),
            Domain(name="another.com", webspace_id=2, cl_id=client_b.id),
            Domain(name="sample.org", webspace_id=0, cl_id=client_c.id),
            Domain(name="example.net", webspace_id=2, cl_id=client_b.id),
        ]

        session.add_all(domain_data)
        session.commit()


def populate_test_db():
    __create_database(TEST_DB_NAME)
    __create_db_and_tables(TEST_DB_NAME)
    __insert_sample_data(TEST_DB_NAME)

def __drop_db_and_tables(db_name: str):
    db_engine = create_engine(
        f"{_connector}://{_user}:{_password}@{_host}/{db_name}"
    )
    SQLModel.metadata.drop_all(db_engine)  # Drop all tables defined in the metadata
    
def cleanup_test_db():
    __drop_db_and_tables(TEST_DB_NAME)  # Drop the test tables