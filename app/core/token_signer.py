import base64
import time
import secrets
import json
import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey
)
from cryptography.hazmat.primitives import serialization

from app.core.config import settings

EXPIRATION_PERIOD_SECONDS = 900


class ToKenSigner:
    def __init__(self):

        if settings.ENVIRONMENT == "local":
            self._private_key_path = "/tmp/test_token_key/priv.key"
            self._public_key_path = "/tmp/test_token_key/pub.key"
            os.makedirs("/tmp/test_token_key", exist_ok=True)

            if os.path.exists(self._private_key_path) and os.path.exists(
                self._public_key_path
            ):
                self._load_keys_from_files()
            else:
                self._generate_and_store_keys()
        else:
            self._private_key = Ed25519PrivateKey.generate()

    def _generate_and_store_keys(self):
        self._private_key = Ed25519PrivateKey.generate()

        private_bytes = self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with open(self._private_key_path, "wb") as f:
            f.write(private_bytes)

        x509_der_pub  = self._private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
        with open(self._public_key_path, "w") as f:
            f.write(base64.b64encode(x509_der_pub).decode())
 
    def _load_keys_from_files(self):
        with open(self._private_key_path, "rb") as f:
            private_bytes = f.read()
            self._private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)

        with open(self._public_key_path, "r") as f:
            public_b64 = f.read().strip()
        public_bytes = base64.b64decode(public_b64)
        self._public_key = serialization.load_der_public_key(public_bytes)

    def _sign_message(self, data):
        signature = self._private_key.sign(data.encode())
        return base64.b64encode(signature).decode()

    def create_signed_token(self, operation):
        timestamp = int(time.time())
        expiry = timestamp + EXPIRATION_PERIOD_SECONDS
        nonce = secrets.token_hex(8)

        token_data = {
            "timestamp": timestamp,
            "nonce": nonce,
            "expiry": expiry,
            "operation": operation,
        }

        message = "|".join(str(item) for item in token_data.values())
        signature = self._sign_message(message)
        token_data["signature"] = signature

        signed_token_json = json.dumps(token_data)
        return base64.b64encode(signed_token_json.encode("utf-8")).decode("utf-8")

    def get_raw_public_key_bytes(self):
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def get_public_key_base64(self):
        x509_der_pub = self._private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
        return base64.b64encode(x509_der_pub).decode()
    
