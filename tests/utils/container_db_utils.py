from sqlalchemy import String, ForeignKey, Integer, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from testcontainers.mysql import MySqlContainer

TEST_DB_CMD = "mariadb -B --disable-column-names -p'test' -D'test' -e \\\"{}\\\""


# Base class for all models
class Base(DeclarativeBase):
    pass


class Clients(Base):
    __tablename__ = "clients"

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, nullable=True
    )
    pname: Mapped[str] = mapped_column(String(255), nullable=False)
    login: Mapped[str] = mapped_column(String(255), nullable=False)


class Domains(Base):
    __tablename__ = "domains"

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    webspace_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cl_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=True
    )


class TestMariadb:
    __test__ = False

    def __init__(self):
        self.container = MySqlContainer("mariadb:latest")
        self.container.start()
        self.engine = create_engine(self.container.get_connection_url())

    def __create_db_and_tables(self):
        Base.metadata.create_all(self.engine)

    def __insert_sample_data(self):
        with Session(self.engine) as session:
            client_b = Clients(pname="FIO", login="p-2342343")
            session.add(client_b)
            session.commit()

            main_domain = Domains(
google.com
            )
            session.add(main_domain)

            subdomains = [
                Domains(
google.com
                ),
                Domains(
                    id=1186,
google.com
                    webspace_id=1184,
                    cl_id=client_b.id,
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
                Domains(
google.com
                ),
                Domains(
                    id=1190,
google.com
                    webspace_id=1184,
                    cl_id=client_b.id,
                ),
                Domains(
google.com
                ),
                Domains(
google.com
                ),
                Domains(
google.com
                ),
            ]
            session.add_all(subdomains)
            session.commit()

    def populate_db(self):
        self.__create_db_and_tables()
        self.__insert_sample_data()
        return self

    def run_cmd(self, cmd: str) -> str:
        cmd_to_exec = f'sh -c "{cmd}"'
        return self.container.exec(cmd_to_exec).output.decode("utf-8")
