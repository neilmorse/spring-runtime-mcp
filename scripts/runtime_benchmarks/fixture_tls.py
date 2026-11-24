"""Issue short-lived loopback certificates for disposable fixtures."""

from __future__ import annotations

import ipaddress
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def write_certificates(directory: Path, *, store_password: bytes | None = None) -> None:
    """Write a public CA and one server identity into a fresh private directory."""
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "Loopback fixture CA")]
    )
    now = datetime.now(UTC)
    builder = (
        x509.CertificateBuilder()
        .issuer_name(ca_name)
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
    )
    ca = (
        builder.subject_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    cert = (
        builder.subject_name(
            x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Loopback fixture")])
        )
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]
            ),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    if store_password is None:
        name = "server.pem"
        identity = server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ) + cert.public_bytes(serialization.Encoding.PEM)
    else:
        name = "server.p12"
        identity = pkcs12.serialize_key_and_certificates(
            b"loopback",
            server_key,
            cert,
            [ca],
            serialization.BestAvailableEncryption(store_password),
        )
    with os.fdopen(
        os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
    ) as output:
        output.write(identity)
    with (directory / "ca.pem").open("xb") as output:
        output.write(ca.public_bytes(serialization.Encoding.PEM))


if __name__ == "__main__":
    # The clean-install gate invokes this file with its isolated interpreter.
    write_certificates(Path(sys.argv[1]))
