from fastapi.testclient import TestClient
from .main import app
from .command_injection_list import COMMAND_INJECTION_LIST
import pytest

example.com
MALFORMED_DOMAIN = "googlecom."


client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_a_record_resolution_with_correct_domain_name():
    response = client.get(f"/resolve-a/{DOMAIN_WITH_EXISTING_A_RECORD}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": DOMAIN_WITH_EXISTING_A_RECORD,
        "value": ["IP_PLACEHOLDER"],
    }


def test_a_record_resolution_with_malformed_domain_name():
    response = client.get(f"/resolve-a/{MALFORMED_DOMAIN}")
    assert response.status_code == 422


def test_ssh_connection():
    correct_response_from_ssh = {
        "host": "vgruzo",
        "stdout": "Hello",
    }
    response = client.get("/plesk/greet")
    assert response.status_code == 200
    assert correct_response_from_ssh in response.json() 

@pytest.mark.parametrize('command', COMMAND_INJECTION_LIST) 
def test_command_injection_security(command):
    response = client.get(f"/resolve/zonemaster/?domain={command}")
    assert response.status_code == 422
    
    
