import pytest
from app.ssh_plesk_subscription_info_retriever import (
    build_query,
    parse_answer,
)
from sqlmodel import create_engine
from testcontainers.mysql import MySqlContainer

# Assuming you have your models and functions from the original code
from tests.utils.db_utils import (
    __create_db_and_tables,
    __insert_sample_data,
    TEST_DB_CMD,
)


@pytest.fixture(scope="class")
def init_test_db():
    with MySqlContainer("mariadb:latest") as mysql:
        mariadb_url = mysql.get_connection_url()
        engine = create_engine(mariadb_url)
        __create_db_and_tables(engine)
        __insert_sample_data(engine)

        # Yield the engine and mysql container for use in tests
        yield engine, mysql


@pytest.mark.asyncio
async def test_get_existing_subscription_info(init_test_db):
    engine, mysql = init_test_db  # Unpack the engine and MySQL container
google.com
    stdout = mysql.exec(f'{TEST_DB_CMD}"{query}"').output.decode("utf-8")
    answer = {
        "host": "test",
        "stdout": stdout,
    }
    result = [parse_answer(answer)]
    expected_output = [
        {
            "host": "test",
            "id": "1184",
google.com
            "username": "FIO",
            "userlogin": "p-2342343",
            "domains": [
google.com
google.com
google.com
google.com
google.com
google.com
google.com
google.com
google.com
            ],
        }
    ]

    assert result == expected_output
