package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"math/big"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// escribirParTLS genera un certificado autofirmado y devuelve las rutas.
func escribirParTLS(t *testing.T) (string, string) {
	t.Helper()
	clave, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	plantilla := &x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject:      pkix.Name{CommonName: "fabric-gateway"},
		NotBefore:    time.Now().Add(-time.Minute),
		NotAfter:     time.Now().Add(time.Hour),
		IPAddresses:  []net.IP{net.ParseIP("127.0.0.1")},
	}
	der, err := x509.CreateCertificate(rand.Reader, plantilla, plantilla, &clave.PublicKey, clave)
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	cert := filepath.Join(dir, "server.crt")
	key := filepath.Join(dir, "server.key")
	if err := os.WriteFile(cert, pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(key, pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(clave)}), 0o600); err != nil {
		t.Fatal(err)
	}
	return cert, key
}

// configurar fija las variables de transporte y las restaura al terminar.
func configurar(t *testing.T, httpAddr, tlsAddr, cert, key string) {
	t.Helper()
	prev := []string{listenAddr, tlsListenAddr, tlsCertPath, tlsKeyPath}
	listenAddr, tlsListenAddr, tlsCertPath, tlsKeyPath = httpAddr, tlsAddr, cert, key
	t.Cleanup(func() {
		listenAddr, tlsListenAddr, tlsCertPath, tlsKeyPath = prev[0], prev[1], prev[2], prev[3]
	})
}

func TestSoloHTTPPorDefecto(t *testing.T) {
	configurar(t, ":8081", "", "", "")
	servers, err := buildServers(http.NewServeMux())
	if err != nil || len(servers) != 1 || servers[0].tls {
		t.Fatalf("se esperaba un listener HTTP, got %v / %v", servers, err)
	}
}

func TestHTTPyHTTPS(t *testing.T) {
	cert, key := escribirParTLS(t)
	configurar(t, ":8081", ":8443", cert, key)
	servers, err := buildServers(http.NewServeMux())
	if err != nil || len(servers) != 2 {
		t.Fatalf("se esperaban dos listeners, got %v / %v", servers, err)
	}
	if servers[1].srv.TLSConfig.MinVersion != 0x0303 {
		t.Fatalf("el minimo debe ser TLS 1.2")
	}
}

func TestSoloHTTPS(t *testing.T) {
	cert, key := escribirParTLS(t)
	configurar(t, "off", ":8443", cert, key)
	servers, err := buildServers(http.NewServeMux())
	if err != nil || len(servers) != 1 || !servers[0].tls {
		t.Fatalf("se esperaba solo el listener HTTPS, got %v / %v", servers, err)
	}
}

func TestHTTPSSinCertificadoNoArranca(t *testing.T) {
	configurar(t, ":8081", ":8443", "", "")
	if _, err := buildServers(http.NewServeMux()); err == nil {
		t.Fatal("HTTPS sin certificado debe fallar")
	}
}

func TestCertificadoIlegibleNoArranca(t *testing.T) {
	configurar(t, ":8081", ":8443", "/no/existe.crt", "/no/existe.key")
	if _, err := buildServers(http.NewServeMux()); err == nil {
		t.Fatal("un certificado inexistente debe fallar al arrancar")
	}
}

func TestSinListenersNoArranca(t *testing.T) {
	configurar(t, "off", "", "", "")
	if _, err := buildServers(http.NewServeMux()); err == nil {
		t.Fatal("sin listeners debe fallar")
	}
}
