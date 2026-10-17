"""TLS hacia el puente Fabric: validacion contra la CA propia y configuracion obligatoria."""

import datetime
import ipaddress
import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from backend.blockchain.fabric_client import FabricClient
from backend.config import Settings


def _nombre(cn):
    """Nombre X.509 con solo CN."""
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def _emitir_ca(cn):
    """CA autofirmada: devuelve (clave, certificado)."""
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ahora = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(_nombre(cn))
        .issuer_name(_nombre(cn))
        .public_key(clave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - datetime.timedelta(minutes=1))
        .not_valid_after(ahora + datetime.timedelta(days=1))
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
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(clave.public_key()), critical=False)
        .sign(clave, hashes.SHA256())
    )
    return clave, cert


def _emitir_servidor(ca_clave, ca_cert):
    """Certificado de servidor para 127.0.0.1 firmado por la CA dada."""
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ahora = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(_nombre("fabric-gateway"))
        .issuer_name(ca_cert.subject)
        .public_key(clave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - datetime.timedelta(minutes=1))
        .not_valid_after(ahora + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_clave.public_key()), critical=False)
        .sign(ca_clave, hashes.SHA256())
    )
    return clave, cert


def _pem(cert):
    """Certificado en PEM como str."""
    return cert.public_bytes(serialization.Encoding.PEM).decode("ascii")


class _Handler(BaseHTTPRequestHandler):
    """Responde /health como el puente."""

    def do_GET(self):  # noqa: N802 - nombre impuesto por BaseHTTPRequestHandler
        """Devuelve un health ok."""
        cuerpo = json.dumps({"status": "ok"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        """Silencia el log del servidor de prueba."""


@pytest.fixture()
def puente_tls(tmp_path):
    """Puente HTTPS local con certificado de una CA propia. Devuelve (url, ca_pem)."""
    ca_clave, ca_cert = _emitir_ca("CA de prueba")
    srv_clave, srv_cert = _emitir_servidor(ca_clave, ca_cert)
    cert_path = tmp_path / "server.crt"
    key_path = tmp_path / "server.key"
    cert_path.write_bytes(srv_cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        srv_clave.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    servidor = HTTPServer(("127.0.0.1", 0), _Handler)
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.load_cert_chain(cert_path, key_path)
    servidor.socket = contexto.wrap_socket(servidor.socket, server_side=True)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"https://127.0.0.1:{servidor.server_address[1]}", _pem(ca_cert)
    servidor.shutdown()
    servidor.server_close()


def test_https_con_la_ca_del_proyecto(puente_tls):
    url, ca_pem = puente_tls
    cliente = FabricClient(base_url=url, auth_token="token", ca_pem=ca_pem)
    assert cliente.health() == {"status": "ok"}


def test_https_rechaza_certificado_de_otra_ca(puente_tls):
    url, _ = puente_tls
    _, otra_ca = _emitir_ca("Otra CA")
    cliente = FabricClient(base_url=url, auth_token="token", ca_pem=_pem(otra_ca))
    assert cliente.health() is None


def test_https_sin_ca_no_confia_en_la_ca_propia(puente_tls):
    """Sin CA configurada se usa el almacen del sistema, que no conoce la CA del proyecto."""
    url, _ = puente_tls
    cliente = FabricClient(base_url=url, auth_token="token")
    cliente._ssl_context = ssl.create_default_context()
    assert cliente.health() is None


def test_http_no_usa_contexto_tls():
    cliente = FabricClient(base_url="http://puente", auth_token="token", ca_pem="ignorada")
    assert cliente._ssl_context is None


def _settings_produccion(**extra):
    """Settings de produccion completos salvo lo que se pise."""
    base = {
        "environment": "production",
        "database_url": "postgresql://u:p@h/db",
        "gateway_auth_token": "token",
        "fabric_gateway_url": "https://172.31.89.189:8443",
        "fabric_gateway_ca_pem": None,
    }
    base.update(extra)
    return Settings(**base)


def test_produccion_con_https_exige_la_ca():
    with pytest.raises(RuntimeError, match="FABRIC_GATEWAY_CA_PEM"):
        _settings_produccion().validate_production_requirements()


def test_produccion_con_https_y_ca_arranca():
    _settings_produccion(fabric_gateway_ca_pem="pem").validate_production_requirements()


def test_produccion_con_http_sigue_admitida():
    """Retrocompatibilidad: una task definition sin TLS sigue arrancando."""
    _settings_produccion(fabric_gateway_url="http://172.31.89.189:8081").validate_production_requirements()
