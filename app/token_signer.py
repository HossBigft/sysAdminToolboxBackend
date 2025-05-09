import base64
import time
import secrets
import json
import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from app.core.config import settings

EXPIRATION_PERIOD_SECONDS = 900


class ToKenSigner:
    def __init__(self):
        self._private_key = Ed25519PrivateKey.generate()

        if settings.ENVIRONMENT == "local":
            self._write_raw_public_key_to_file()

    def _write_raw_public_key_to_file(self):
        os.makedirs("/app/test_token_key", exist_ok=True)
        raw_key_bytes = self.get_raw_public_key_bytes()
        
        raw_key_base64 = base64.b64encode(raw_key_bytes).decode('utf-8')
        
        with open("/app/test_token_key/pub.key", "w") as f:
            f.write(raw_key_base64)

    def _sign_message(self, data):
        signature = self._private_key.sign(data.encode())
        return base64.b64encode(signature).decode()

    def create_signed_token(self, command):
        timestamp = int(time.time())
        expiry = timestamp + EXPIRATION_PERIOD_SECONDS
        nonce = secrets.token_hex(8)

        token_data = {
            "timestamp": timestamp,
            "nonce": nonce,
            "expiry": expiry,
            "command": command
        }

        message = "|".join(str(item) for item in token_data.values())

        signature = self._sign_message(message)
        token_data["signature"] = signature

        signed_token_json = json.dumps(token_data)
        encoded_json = base64.b64encode(signed_token_json.encode('utf-8')).decode('utf-8')
        return encoded_json

    def get_raw_public_key_bytes(self):
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
