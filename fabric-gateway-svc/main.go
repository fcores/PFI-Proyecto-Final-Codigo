// fabric-gateway-svc es un servicio HTTP minimo que actua como puente entre
// el backend Python (FastAPI) y la red Hyperledger Fabric via el SDK Gateway.
// Corre en la misma EC2 que la red Fabric, accesible solo desde el SG del backend.
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

var (
	listenAddr     = envOrDefault("LISTEN_ADDR", ":8081")
	channelName    = envOrDefault("CHANNEL_NAME", "mychannel")
	chaincodeName  = envOrDefault("CHAINCODE_NAME", "prescriptions")
	mspID          = envOrDefault("MSP_ID", "Org1MSP")
	peerEndpoint   = envOrDefault("PEER_ENDPOINT", "localhost:7051")
	certPath       = envOrDefault("CERT_PATH", "")
	keyPath        = envOrDefault("KEY_PATH", "")
	tlsCertPath    = envOrDefault("TLS_CERT_PATH", "")
)

func envOrDefault(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}

// InvokeRequest es el payload para invocar una transaccion.
type InvokeRequest struct {
	Function string   `json:"function"`
	Args     []string `json:"args"`
}

// InvokeResponse es la respuesta de una invocacion.
type InvokeResponse struct {
	TxID    string `json:"tx_id"`
	Payload string `json:"payload,omitempty"`
	Error   string `json:"error,omitempty"`
}

// QueryRequest es el payload para evaluar (query) sin commit.
type QueryRequest struct {
	Function string   `json:"function"`
	Args     []string `json:"args"`
}

func main() {
	log.Printf("fabric-gateway-svc iniciando en %s (channel=%s, chaincode=%s)", listenAddr, channelName, chaincodeName)

	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/invoke", invokeHandler)
	http.HandleFunc("/query", queryHandler)

	server := &http.Server{
		Addr:         listenAddr,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 60 * time.Second,
	}

	if err := server.ListenAndServe(); err != nil {
		log.Fatalf("Error al iniciar servidor: %v", err)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status":    "ok",
		"service":   "fabric-gateway-svc",
		"channel":   channelName,
		"chaincode": chaincodeName,
	})
}

func invokeHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req InvokeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("JSON invalido: %v", err))
		return
	}

	// TODO: conectar con Fabric Gateway SDK real
	// Por ahora retorna un placeholder para que el backend pueda integrarse
	log.Printf("INVOKE %s(%v)", req.Function, req.Args)

	resp := InvokeResponse{
		TxID:  fmt.Sprintf("tx_%d", time.Now().UnixNano()),
		Error: "",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func queryHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req QueryRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("JSON invalido: %v", err))
		return
	}

	log.Printf("QUERY %s(%v)", req.Function, req.Args)

	// TODO: conectar con Fabric Gateway SDK real
	resp := InvokeResponse{
		Payload: "{}",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(InvokeResponse{Error: msg})
}
