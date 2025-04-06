from sqlalchemy import String, ForeignKey, Integer, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from testcontainers.mysql import MySqlContainer
from enum import IntEnum

TEST_DB_CMD = "mariadb -B --disable-column-names -p'test' -D'test' -e \\\"{}\\\""


class Base(DeclarativeBase):
    pass


class DomainStatus(IntEnum):
    ONLINE = 0
    SUBSCRIPTION_DISABLED = 2
    DISABLED_BY_ADMIN = 16
    DISABLED_BY_CLIENT = 64


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
    status: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DomainStatus.ONLINE.value
    )
    overuse: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    real_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=317 * 1024 * 1024
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
            client_b = Clients(pname="USER_NAME", login="p-341161")
            session.add(client_b)
            session.commit()

            main_domain = Domains(
                id=1184,
                name="google.com",
                webspace_id=0,
                cl_id=client_b.id,
                status=DomainStatus.ONLINE.value,
            )
            session.add(main_domain)

            subdomains = [
                Domains(
                    id=1185,
                    name="test.google.com",
                    webspace_id=1184,
                    cl_id=client_b.id,
                    status=DomainStatus.SUBSCRIPTION_DISABLED.value,
                ),
                Domains(
                    id=1186,
                    name="mx.google.com",
                    webspace_id=1184,
                    cl_id=client_b.id,
                    status=DomainStatus.DISABLED_BY_ADMIN.value,
                ),
                Domains(
                    id=1187,
                    name="zless.zlessgoogle.com",
                    webspace_id=1184,
                    cl_id=client_b.id,
                    status=DomainStatus.DISABLED_BY_CLIENT.value,
                ),
                Domains(
                    id=1188,
                    name="1.google.com",
                    webspace_id=1184,
                    cl_id=client_b.id,
                    status=DomainStatus.ONLINE.value,
                ),
                Domains(
                    id=1189,
                    name="gog.google.com",
                    webspace_id=1184,
                    cl_id=client_b.id,
                    status=DomainStatus.SUBSCRIPTION_DISABLED.value,
                ),
                Domains(
                    id=1190,
                    name="asd.google.com",
                    webspace_id=1184,
                    cl_id=client_b.id,
                    status=DomainStatus.DISABLED_BY_ADMIN.value,
                ),
                Domains(
                    id=1378,
                    name="oht.google.com",
                    webspace_id=1184,
                    cl_id=client_b.id,
                    status=DomainStatus.DISABLED_BY_CLIENT.value,
                ),
                Domains(
                    id=1379,
                    name="ts.google.com",
                    webspace_id=1184,
                    cl_id=client_b.id,
                    status=DomainStatus.ONLINE.value,
                ),
                Domains(
                    id=1383,
                    name="lkok.google.com",
                    webspace_id=1184,
                    cl_id=client_b.id,
                    status=DomainStatus.SUBSCRIPTION_DISABLED.value,
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
