from sqlmodel import Field, Session, SQLModel, create_engine, text

_user = "vtest"
_password = "Guakufooquaek7Houph0"
_connector = "mariadb+pymysql"
_host = "IP_PLACEHOLDER"

TEST_DB_NAME = "testdb"
TEST_DB_CMD = f"mysql -B --disable-column-names -p'{_password}' -D'{TEST_DB_NAME}' -e"


# Define the Client model
class Clients(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    pname: str = Field(..., max_length=255)  # Use max_length for VARCHAR
    login: str = Field(..., max_length=255)  # Use max_length for VARCHAR


# Define the Domain model
class Domains(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(..., max_length=255)  # Specify length
    webspace_id: int
    cl_id: int = Field(default=None, foreign_key="clients.id")


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
        client_b = Clients(pname="FIO", login="p-2342343")
        session.add(client_b)
        session.commit()

        # Create the main domain with a specific ID
        main_domain = Domains(
google.com
        )
        session.add(main_domain)

        # Create subdomains with specific IDs, all linked to the main domain ID
        subdomains = [
            Domains(
google.com
            ),
            Domains(
google.com
            ),
            Domains(
google.com
            ),
            Domains(
                id=1188,
google.com
                webspace_id=1184,
                cl_id=client_b.id,
            ),
google.com
            Domains(
google.com
            ),
            Domains(
google.com
            ),
google.com
            Domains(
google.com
            ),
        ]

        session.add_all(subdomains)
        session.commit()


def populate_test_db():
    __create_database(TEST_DB_NAME)
    __create_db_and_tables(TEST_DB_NAME)
    __insert_sample_data(TEST_DB_NAME)


def __drop_db_and_tables(db_name: str):
    db_engine = create_engine(f"{_connector}://{_user}:{_password}@{_host}/{db_name}")
    SQLModel.metadata.drop_all(db_engine)  # Drop all tables defined in the metadata


def cleanup_test_db():
    __drop_db_and_tables(TEST_DB_NAME)  # Drop the test tables
