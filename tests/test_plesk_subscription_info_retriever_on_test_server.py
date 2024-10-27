import pytest
from tests.utils.db_utils import populate_test_db, cleanup_test_db

@pytest.fixture(scope="class",autouse=True)
def init_test_db():
    populate_test_db()
    yield
    cleanup_test_db()
    
def test():
    print("asra")