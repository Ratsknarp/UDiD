from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import NameOID
import cryptography.x509 as x509
import io
from typing import Tuple
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    pkcs12,
    load_pem_private_key,
)
from cryptography.hazmat.backends import default_backend


class KeyManager:
    @staticmethod
    def generate_keys() -> Tuple[bytes, bytes]:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        csr_builder = x509.CertificateSigningRequestBuilder()
        csr = csr_builder.subject_name(
            x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, "CSR File"),
                ]
            )
        ).sign(private_key, hashes.SHA256())

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        csr_pem = csr.public_bytes(serialization.Encoding.PEM)

        return private_key_pem, csr_pem

    @staticmethod
    def convert_cert_to_pem(cert_file: bytes):
        cert = x509.load_der_x509_certificate(cert_file, default_backend())
        pem_data = cert.public_bytes(encoding=serialization.Encoding.PEM)
        return pem_data

    @staticmethod
    def generate_p12(key_file: bytes, pem_file: bytes, password: str):
        private_key = load_pem_private_key(
            key_file, password=None, backend=default_backend()
        )
        cert = x509.load_pem_x509_certificate(pem_file, default_backend())
        additional_certificates = []
        pfx = pkcs12.serialize_key_and_certificates(
            name=b"P12 File",
            key=private_key,
            cert=cert,
            cas=additional_certificates,
            encryption_algorithm=BestAvailableEncryption(password.encode()),
        )
        return pfx
