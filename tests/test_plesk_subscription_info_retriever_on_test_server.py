import pytest
from app.ssh_plesk_subscription_info_retriever import (
    build_query,
    parse_answer,
)


# Assuming you have your models and functions from the original code
from tests.utils.db_utils import TestMariadb


@pytest.fixture(scope="class")
def test_db():
    testdb = TestMariadb().populate_db()
    yield testdb
    testdb.cleanup()

@pytest.mark.asyncio
async def test_get_existing_subscription_info(test_db):
google.com
    stdout = test_db.run_query(query)
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
