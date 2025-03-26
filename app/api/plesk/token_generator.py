import base64
import time
import secrets

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


EXPIRATION_PERIOD = 90


class TokenSigner:
    def __init__(self):
        self._private_key = Ed25519PrivateKey.generate()

    def _sign_with_ed25519(self, data):
        signature = self._private_key.sign(data.encode())
        return base64.b64encode(signature).decode()

    def generate_command_token(self, command):
        timestamp = int(time.time())
        expiry = timestamp + EXPIRATION_PERIOD
        nonce = secrets.token_hex(8)

        message = f"{timestamp}|{nonce}|{expiry}|{command}"

        signature = self._sign_with_ed25519(message)

        token = f"{message}|{signature}"

        return token

    def public_key_pem(self):
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
