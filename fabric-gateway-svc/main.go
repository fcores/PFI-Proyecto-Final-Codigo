// fabric-gateway-svc es el puente HTTP entre el backend Python (FastAPI) y la
// red Hyperledger Fabric, implementado sobre el Fabric Gateway SDK.
//
// Mantiene UNA conexion por organizacion (Prescriptor, MedChain, Prepaga) y
// firma cada transaccion con la identidad de la org correspondiente al campo
// "actor" del request:
//
//   actor=prescriptor -> PrescriptorMSP (unico autorizado a CreatePrescription)
//   actor=auditor     -> MedChainMSP    (unico autorizado a AuditPrescription)
//   actor=prepaga     -> PrepagaMSP     (default para lecturas)
//
// Asi el control de acceso por MSP del chaincode se ejerce de verdad: la firma
// de la transaccion pertenece a la organizacion que corresponde al rol.
//
// Autenticacion de entrada: header X-Gateway-Token (comparacion en tiempo
// constante contra GATEWAY_AUTH_TOKEN). /health queda libre.
//
// Transporte: HTTPS en TLS_LISTEN_ADDR (certificado de una CA propia del
// proyecto, ver fabric/scripts/gateway-tls.sh) y, opcionalmente, HTTP plano en
// LISTEN_ADDR. LISTEN_ADDR=off apaga el HTTP; sin definir vale ":8081" para no
// romper un despliegue que todavia no tenga certificados. Los dos listeners
// comparten handlers, token y conexiones a los peers.
//
// Corre en la misma red Docker que los peers (local y en la EC2); sus puertos
// solo deben ser accesibles desde la red de la aplicacion.
package main

import (
	"crypto/subtle"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/hyperledger/fabric-gateway/pkg/client"
	"github.com/hyperledger/fabric-gateway/pkg/identity"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
)

// ──────────────────────────── Configuración ─────────────────────────────────

var (
	listenAddr    = envOrDefault("LISTEN_ADDR", ":8081")
	tlsListenAddr = os.Getenv("TLS_LISTEN_ADDR")
	tlsCertPath   = os.Getenv("TLS_CERT_PATH")
	tlsKeyPath    = os.Getenv("TLS_KEY_PATH")
	channelName   = envOrDefault("CHANNEL_NAME", "mychannel")
	chaincodeName = envOrDefault("CHAINCODE_NAME", "prescriptions")
	gatewayToken  = os.Getenv("GATEWAY_AUTH_TOKEN")
)

func envOrDefault(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}

// orgConfig es la configuración de conexión de una organización.
type orgConfig struct {
	Actor        string // valor del campo "actor" en los requests
	MSPID        string
	PeerEndpoint string
	CertPath     string // archivo o directorio signcerts del usuario
	KeyPath      string // archivo o directorio keystore del usuario
	TLSCertPath  string // CA TLS del peer
}

func loadOrgConfigs() []orgConfig {
	return []orgConfig{
		{
			Actor:        "prescriptor",
			MSPID:        envOrDefault("PRESCRIPTOR_MSP_ID", "PrescriptorMSP"),
			PeerEndpoint: envOrDefault("PRESCRIPTOR_PEER_ENDPOINT", "localhost:7051"),
			CertPath:     os.Getenv("PRESCRIPTOR_CERT_PATH"),
			KeyPath:      os.Getenv("PRESCRIPTOR_KEY_PATH"),
			TLSCertPath:  os.Getenv("PRESCRIPTOR_TLS_CERT_PATH"),
		},
		{
			Actor:        "auditor",
			MSPID:        envOrDefault("MEDCHAIN_MSP_ID", "MedChainMSP"),
			PeerEndpoint: envOrDefault("MEDCHAIN_PEER_ENDPOINT", "localhost:9051"),
			CertPath:     os.Getenv("MEDCHAIN_CERT_PATH"),
			KeyPath:      os.Getenv("MEDCHAIN_KEY_PATH"),
			TLSCertPath:  os.Getenv("MEDCHAIN_TLS_CERT_PATH"),
		},
		{
			Actor:        "prepaga",
			MSPID:        envOrDefault("PREPAGA_MSP_ID", "PrepagaMSP"),
			PeerEndpoint: envOrDefault("PREPAGA_PEER_ENDPOINT", "localhost:11051"),
			CertPath:     os.Getenv("PREPAGA_CERT_PATH"),
			KeyPath:      os.Getenv("PREPAGA_KEY_PATH"),
			TLSCertPath:  os.Getenv("PREPAGA_TLS_CERT_PATH"),
		},
	}
}

// Reglas de autorización de invokes: cada función de escritura solo puede
// firmarse con la identidad del actor que corresponde.
var invokeActorPorFuncion = map[string]string{
	"CreatePrescription": "prescriptor",
	"AuditPrescription":  "auditor",
	"InitLedger":         "prescriptor",
}

// Funciones de lectura permitidas vía /query.
var queryFunciones = map[string]bool{
	"GetPrescription":             true,
	"ListPrescriptions":           true,
	"QueryPrescriptionsByEstado":  true,
	"QueryPrescriptionsByPatient": true,
	"GetPrescriptionHistory":      true,
}

// ─────────────────────────── Conexiones Fabric ──────────────────────────────

// orgGateway agrupa la conexión viva de una organización.
type orgGateway struct {
	cfg      orgConfig
	gateway  *client.Gateway
	contract *client.Contract
}

// readPEM lee un PEM desde un archivo, o desde el primer archivo de un
// directorio (cryptogen nombra la key del keystore de forma no predecible).
func readPEM(path string) ([]byte, error) {
	info, err := os.Stat(path)
	if err != nil {
		return nil, err
	}
	if !info.IsDir() {
		return os.ReadFile(path)
	}
	entries, err := os.ReadDir(path)
	if err != nil {
		return nil, err
	}
	for _, e := range entries {
		if !e.IsDir() {
			return os.ReadFile(filepath.Join(path, e.Name()))
		}
	}
	return nil, fmt.Errorf("directorio %s vacio", path)
}

func connectOrg(cfg orgConfig) (*orgGateway, error) {
	if cfg.CertPath == "" || cfg.KeyPath == "" || cfg.TLSCertPath == "" {
		return nil, fmt.Errorf("org %s (%s): faltan CERT_PATH/KEY_PATH/TLS_CERT_PATH", cfg.Actor, cfg.MSPID)
	}

	transportCredentials, err := credentials.NewClientTLSFromFile(cfg.TLSCertPath, "")
	if err != nil {
		return nil, fmt.Errorf("org %s: error cargando TLS CA: %w", cfg.Actor, err)
	}
	connection, err := grpc.NewClient(cfg.PeerEndpoint, grpc.WithTransportCredentials(transportCredentials))
	if err != nil {
		return nil, fmt.Errorf("org %s: error creando conexion gRPC: %w", cfg.Actor, err)
	}

	certificatePEM, err := readPEM(cfg.CertPath)
	if err != nil {
		return nil, fmt.Errorf("org %s: error leyendo certificado: %w", cfg.Actor, err)
	}
	certificate, err := identity.CertificateFromPEM(certificatePEM)
	if err != nil {
		return nil, fmt.Errorf("org %s: certificado invalido: %w", cfg.Actor, err)
	}
	id, err := identity.NewX509Identity(cfg.MSPID, certificate)
	if err != nil {
		return nil, fmt.Errorf("org %s: error creando identidad: %w", cfg.Actor, err)
	}

	privateKeyPEM, err := readPEM(cfg.KeyPath)
	if err != nil {
		return nil, fmt.Errorf("org %s: error leyendo clave privada: %w", cfg.Actor, err)
	}
	privateKey, err := identity.PrivateKeyFromPEM(privateKeyPEM)
	if err != nil {
		return nil, fmt.Errorf("org %s: clave privada invalida: %w", cfg.Actor, err)
	}
	sign, err := identity.NewPrivateKeySign(privateKey)
	if err != nil {
		return nil, fmt.Errorf("org %s: error creando firmador: %w", cfg.Actor, err)
	}

	gw, err := client.Connect(
		id,
		client.WithSign(sign),
		client.WithClientConnection(connection),
		client.WithEvaluateTimeout(15*time.Second),
		client.WithEndorseTimeout(15*time.Second),
		client.WithSubmitTimeout(30*time.Second),
		client.WithCommitStatusTimeout(30*time.Second),
	)
	if err != nil {
		return nil, fmt.Errorf("org %s: error conectando al gateway: %w", cfg.Actor, err)
	}

	contract := gw.GetNetwork(channelName).GetContract(chaincodeName)
	return &orgGateway{cfg: cfg, gateway: gw, contract: contract}, nil
}

// gateways por actor ("prescriptor" | "auditor" | "prepaga").
var gateways = map[string]*orgGateway{}

// ──────────────────────────────── HTTP ──────────────────────────────────────

// InvokeRequest es el payload para invocar una transaccion (submit + commit).
type InvokeRequest struct {
	Function string   `json:"function"`
	Args     []string `json:"args"`
	Actor    string   `json:"actor"`
}

// QueryRequest es el payload para evaluar (query) sin commit.
type QueryRequest struct {
	Function string   `json:"function"`
	Args     []string `json:"args"`
	Actor    string   `json:"actor"`
}

// GatewayResponse es la respuesta uniforme de /invoke y /query.
type GatewayResponse struct {
	TxID      string `json:"tx_id,omitempty"`
	Payload   string `json:"payload,omitempty"`
	Error     string `json:"error,omitempty"`
	ErrorType string `json:"error_type,omitempty"`
}

func main() {
	if gatewayToken == "" {
		log.Fatal("GATEWAY_AUTH_TOKEN es obligatorio (auth del puente); definirlo en el entorno")
	}

	for _, cfg := range loadOrgConfigs() {
		gw, err := connectOrg(cfg)
		if err != nil {
			log.Fatalf("Error conectando la org %s: %v", cfg.Actor, err)
		}
		gateways[cfg.Actor] = gw
		log.Printf("Conectado: actor=%s msp=%s peer=%s", cfg.Actor, cfg.MSPID, cfg.PeerEndpoint)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	mux.HandleFunc("/invoke", requireToken(invokeHandler))
	mux.HandleFunc("/query", requireToken(queryHandler))

	servers, err := buildServers(mux)
	if err != nil {
		log.Fatal(err)
	}

	// Si cualquiera de los listeners cae, el proceso termina: un gateway que
	// sirve a medias es peor que uno caido que Docker reinicia.
	errc := make(chan error, len(servers))
	for _, s := range servers {
		go func(s *listener) { errc <- s.serve() }(s)
	}
	log.Fatalf("Error en el servidor: %v", <-errc)
}

// listener es un http.Server con su modo de transporte.
type listener struct {
	srv *http.Server
	tls bool
}

func (l *listener) serve() error {
	if l.tls {
		log.Printf("fabric-gateway-svc escuchando HTTPS en %s (channel=%s, chaincode=%s)", l.srv.Addr, channelName, chaincodeName)
		return l.srv.ListenAndServeTLS(tlsCertPath, tlsKeyPath)
	}
	log.Printf("fabric-gateway-svc escuchando HTTP en %s (channel=%s, chaincode=%s)", l.srv.Addr, channelName, chaincodeName)
	return l.srv.ListenAndServe()
}

// buildServers arma los listeners segun la configuracion. Falla si no queda
// ninguno o si se pidio HTTPS sin certificado legible: mejor no arrancar que
// arrancar sin el cifrado que se configuro.
func buildServers(handler http.Handler) ([]*listener, error) {
	var servers []*listener
	newServer := func(addr string) *http.Server {
		return &http.Server{
			Addr:         addr,
			Handler:      handler,
			ReadTimeout:  30 * time.Second,
			WriteTimeout: 90 * time.Second,
		}
	}

	if listenAddr != "off" {
		servers = append(servers, &listener{srv: newServer(listenAddr)})
	}

	if tlsListenAddr != "" {
		if tlsCertPath == "" || tlsKeyPath == "" {
			return nil, errors.New("TLS_LISTEN_ADDR requiere TLS_CERT_PATH y TLS_KEY_PATH")
		}
		// Se carga una vez aca solo para fallar al arrancar si el par es invalido;
		// ListenAndServeTLS lo vuelve a leer.
		if _, err := tls.LoadX509KeyPair(tlsCertPath, tlsKeyPath); err != nil {
			return nil, fmt.Errorf("certificado TLS del gateway invalido: %w", err)
		}
		srv := newServer(tlsListenAddr)
		srv.TLSConfig = &tls.Config{MinVersion: tls.VersionTLS12}
		servers = append(servers, &listener{srv: srv, tls: true})
	}

	if len(servers) == 0 {
		return nil, errors.New("sin listeners: LISTEN_ADDR=off y TLS_LISTEN_ADDR vacia")
	}
	return servers, nil
}

// requireToken exige el header X-Gateway-Token (comparacion en tiempo constante).
func requireToken(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		provided := r.Header.Get("X-Gateway-Token")
		if subtle.ConstantTimeCompare([]byte(provided), []byte(gatewayToken)) != 1 {
			writeJSON(w, http.StatusUnauthorized, GatewayResponse{Error: "token invalido", ErrorType: "auth"})
			return
		}
		next(w, r)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	type orgHealth struct {
		MSPID  string `json:"msp_id"`
		Peer   string `json:"peer"`
		Status string `json:"status"`
		Error  string `json:"error,omitempty"`
	}
	overall := "ok"
	orgs := map[string]orgHealth{}
	for actor, gw := range gateways {
		oh := orgHealth{MSPID: gw.cfg.MSPID, Peer: gw.cfg.PeerEndpoint, Status: "ok"}
		if _, err := gw.contract.EvaluateTransaction("ListPrescriptions", "1", ""); err != nil {
			oh.Status = "error"
			oh.Error = err.Error()
			overall = "degraded"
		}
		orgs[actor] = oh
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":    overall,
		"service":   "fabric-gateway-svc",
		"channel":   channelName,
		"chaincode": chaincodeName,
		"orgs":      orgs,
	})
}

func invokeHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, GatewayResponse{Error: "metodo no permitido", ErrorType: "bad_request"})
		return
	}

	var req InvokeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, GatewayResponse{Error: fmt.Sprintf("JSON invalido: %v", err), ErrorType: "bad_request"})
		return
	}

	actorRequerido, conocido := invokeActorPorFuncion[req.Function]
	if !conocido {
		writeJSON(w, http.StatusBadRequest, GatewayResponse{
			Error: fmt.Sprintf("funcion de escritura desconocida: %s", req.Function), ErrorType: "bad_request",
		})
		return
	}
	if req.Actor != actorRequerido {
		writeJSON(w, http.StatusBadRequest, GatewayResponse{
			Error:     fmt.Sprintf("la funcion %s requiere actor=%s", req.Function, actorRequerido),
			ErrorType: "bad_request",
		})
		return
	}

	gw := gateways[actorRequerido]
	log.Printf("INVOKE actor=%s msp=%s %s", req.Actor, gw.cfg.MSPID, req.Function)

	result, commit, err := gw.contract.SubmitAsync(req.Function, client.WithArguments(req.Args...))
	if err != nil {
		writeFabricError(w, err, "")
		return
	}

	txID := commit.TransactionID()
	status, err := commit.Status()
	if err != nil {
		writeFabricError(w, err, txID)
		return
	}
	if !status.Successful {
		writeJSON(w, http.StatusBadGateway, GatewayResponse{
			TxID:      txID,
			Error:     fmt.Sprintf("la transaccion no fue validada: codigo %d", int32(status.Code)),
			ErrorType: "commit_failed",
		})
		return
	}

	writeJSON(w, http.StatusOK, GatewayResponse{TxID: txID, Payload: string(result)})
}

func queryHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, GatewayResponse{Error: "metodo no permitido", ErrorType: "bad_request"})
		return
	}

	var req QueryRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, GatewayResponse{Error: fmt.Sprintf("JSON invalido: %v", err), ErrorType: "bad_request"})
		return
	}

	if !queryFunciones[req.Function] {
		writeJSON(w, http.StatusBadRequest, GatewayResponse{
			Error: fmt.Sprintf("funcion de lectura desconocida: %s", req.Function), ErrorType: "bad_request",
		})
		return
	}

	actor := req.Actor
	if actor == "" {
		actor = "prepaga"
	}
	gw, ok := gateways[actor]
	if !ok {
		writeJSON(w, http.StatusBadRequest, GatewayResponse{
			Error: fmt.Sprintf("actor desconocido: %s (usar prescriptor|auditor|prepaga)", actor), ErrorType: "bad_request",
		})
		return
	}

	log.Printf("QUERY actor=%s msp=%s %s", actor, gw.cfg.MSPID, req.Function)

	result, err := gw.contract.EvaluateTransaction(req.Function, req.Args...)
	if err != nil {
		writeFabricError(w, err, "")
		return
	}

	writeJSON(w, http.StatusOK, GatewayResponse{Payload: string(result)})
}

// writeFabricError mapea los errores tipados del SDK a HTTP + error_type.
// 502: fallo de endorsement/submit/evaluate (incluye errores de negocio del
// chaincode: MSP no autorizado, transicion invalida, "ya existe", etc.).
// 504: timeout esperando el estado del commit.
func writeFabricError(w http.ResponseWriter, err error, txID string) {
	var endorseErr *client.EndorseError
	var submitErr *client.SubmitError
	var commitStatusErr *client.CommitStatusError

	switch {
	case errors.As(err, &endorseErr):
		writeJSON(w, http.StatusBadGateway, GatewayResponse{
			TxID: endorseErr.TransactionID, Error: endorseErr.Error(), ErrorType: "endorse",
		})
	case errors.As(err, &submitErr):
		writeJSON(w, http.StatusBadGateway, GatewayResponse{
			TxID: submitErr.TransactionID, Error: submitErr.Error(), ErrorType: "submit",
		})
	case errors.As(err, &commitStatusErr):
		writeJSON(w, http.StatusGatewayTimeout, GatewayResponse{
			TxID: commitStatusErr.TransactionID, Error: commitStatusErr.Error(), ErrorType: "commit_status",
		})
	default:
		writeJSON(w, http.StatusBadGateway, GatewayResponse{
			TxID: txID, Error: err.Error(), ErrorType: "fabric",
		})
	}
}

func writeJSON(w http.ResponseWriter, status int, body interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(body)
}
