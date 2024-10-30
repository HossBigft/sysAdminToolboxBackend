from sqlmodel import Field, Session, SQLModel, create_engine, text
from testcontainers.mysql import MySqlContainer


TEST_DB_CMD = "mariadb -B --disable-column-names -p'test' -D'test' -e"


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


# Create the tables in the database
def __create_db_and_tables(engine):
    SQLModel.metadata.create_all(engine)


def __insert_sample_data(engine):
    with Session(engine) as session:
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
    with MySqlContainer("mariadb:latest") as mysql:
        mariadb_url = mysql.get_connection_url()
        engine = create_engine(mariadb_url)
        __create_db_and_tables(engine)
        __insert_sample_data(engine)
        return engine


if __name__ == "__main__":
    engine = populate_test_db()
