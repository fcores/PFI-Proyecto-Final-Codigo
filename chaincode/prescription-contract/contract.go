// Package main implementa el chaincode PrescriptionContract para prescripciones
// oncologicas. La prescripcion vive UNICAMENTE en el world state (no hay copia
// off-chain): el asset porta el payload clinico completo (seudonimizado via
// patient_id) mas el veredicto del modelo ML.
//
// Garantias que impone el contrato:
//   - Control de acceso por MSP: solo PrescriptorMSP crea, solo MedChainMSP
//     audita; las tres organizaciones (Prescriptor, MedChain, Prepaga) leen.
//   - Maquina de estados validada on-chain:
//     PENDIENTE_AUDITORIA -> EN_REVISION -> APROBADA | RECHAZADA
//     (tambien PENDIENTE_AUDITORIA -> APROBADA | RECHAZADA directo).
//   - Cadena de hashes verificable desde afuera (ver docs/HASHING.md):
//     payload_hash = SHA256(json canonico recibido, byte a byte);
//     event_hash_i = SHA256(prev | accion | estado | auditor | SHA256(justif) | ts).
//
// Regla de determinismo: PROHIBIDO time.Now() y toda fuente local. Los
// timestamps salen de GetTxTimestamp() (proposal del cliente, identico para
// todos los endorsers) o del propio payload firmado.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strconv"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// PrescriptionContract gestiona prescripciones en Hyperledger Fabric.
type PrescriptionContract struct {
	contractapi.Contract
}

const (
	docTypePrescription = "prescription"
	keyPrefix           = "PRESC_"

	// Estados del ciclo de auditoria (los administra este contrato).
	EstadoPendienteAuditoria = "PENDIENTE_AUDITORIA"
	EstadoEnRevision         = "EN_REVISION"
	EstadoAprobada           = "APROBADA"
	EstadoRechazada          = "RECHAZADA"

	// Acciones del auditor.
	AccionRevision = "revision"
	AccionAprobar  = "aprobar"
	AccionRechazar = "rechazar"

	// Organizaciones de la red.
	MSPPrescriptor = "PrescriptorMSP"
	MSPMedChain    = "MedChainMSP"
	MSPPrepaga     = "PrepagaMSP"

	maxJustificacion = 2000
	defaultPageSize  = 50
	maxPageSize      = 200
)

// transicionesValidas define la maquina de estados del ciclo de auditoria.
// La misma tabla esta espejada en tests/fakes/fake_fabric_gateway.py del
// backend; si se modifica aca hay que actualizarla alla.
var transicionesValidas = map[string][]string{
	EstadoPendienteAuditoria: {EstadoEnRevision, EstadoAprobada, EstadoRechazada},
	EstadoEnRevision:         {EstadoAprobada, EstadoRechazada},
	EstadoAprobada:           {},
	EstadoRechazada:          {},
}

// AuditEvent es un eslabon de la cadena de auditoria de una prescripcion.
type AuditEvent struct {
	Seq              int    `json:"seq"`
	Accion           string `json:"accion"`
	EstadoResultante string `json:"estado_resultante"`
	Auditor          string `json:"auditor"`
	Justificacion    string `json:"justificacion"`
	Timestamp        string `json:"timestamp"`
	TxID             string `json:"tx_id"`
	PrevHash         string `json:"prev_hash"`
	EventHash        string `json:"event_hash"`
}

// PrescriptionAsset es el registro on-chain completo de una prescripcion.
// clinical y ml se almacenan como JSON crudo, byte a byte igual que el payload
// canonico recibido en CreatePrescription: eso hace verificable payload_hash
// sin depender de como serializa cada lenguaje.
type PrescriptionAsset struct {
	DocType          string          `json:"docType"`
	PrescriptionID   string          `json:"prescription_id"`
	PrescriptionCode string          `json:"prescription_code"`
	Estado           string          `json:"estado"`
	Clinical         json.RawMessage `json:"clinical"`
	ML               json.RawMessage `json:"ml"`
	CreatedAt        string          `json:"created_at"`
	CreatedByMSP     string          `json:"created_by_msp"`
	PayloadHash      string          `json:"payload_hash"`
	CurrentHash      string          `json:"current_hash"`
	AuditEvents      []AuditEvent    `json:"audit_events"`
}

// PagedPrescriptions es el resultado paginado de los listados.
type PagedPrescriptions struct {
	Items        []*PrescriptionAsset `json:"items"`
	FetchedCount int32                `json:"fetched_count"`
	Bookmark     string               `json:"bookmark"`
}

// canonicalPayload refleja el JSON canonico que envia el backend: claves en
// orden alfabetico (clinical, created_at, ml), sin espacios.
type canonicalPayload struct {
	Clinical  json.RawMessage `json:"clinical"`
	CreatedAt string          `json:"created_at"`
	ML        json.RawMessage `json:"ml"`
}

// ─────────────────────────── Funciones puras ────────────────────────────────

func sha256Hex(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

// validarTransicion verifica que el pasaje de estado sea legal.
func validarTransicion(actual, nueva string) error {
	permitidas, ok := transicionesValidas[actual]
	if !ok {
		return fmt.Errorf("estado actual desconocido: %s", actual)
	}
	for _, p := range permitidas {
		if p == nueva {
			return nil
		}
	}
	return fmt.Errorf("transicion invalida: %s -> %s", actual, nueva)
}

// estadoPorAccion mapea la accion del auditor al estado resultante.
func estadoPorAccion(accion string) (string, error) {
	switch accion {
	case AccionRevision:
		return EstadoEnRevision, nil
	case AccionAprobar:
		return EstadoAprobada, nil
	case AccionRechazar:
		return EstadoRechazada, nil
	default:
		return "", fmt.Errorf("accion desconocida: %s (usar %s|%s|%s)", accion, AccionRevision, AccionAprobar, AccionRechazar)
	}
}

// computeEventHash calcula el eslabon de la cadena de auditoria.
// Convencion (docs/HASHING.md):
//
//	SHA256(prev_hash|accion|estado_resultante|auditor|SHA256(justificacion)|timestamp)
//
// La justificacion se hashea aparte para que el eslabon tenga largo acotado y
// no dependa de caracteres especiales.
func computeEventHash(prevHash, accion, estadoResultante, auditor, justificacion, timestamp string) string {
	material := prevHash + "|" + accion + "|" + estadoResultante + "|" + auditor + "|" +
		sha256Hex([]byte(justificacion)) + "|" + timestamp
	return sha256Hex([]byte(material))
}

// requireMSP valida que el MSP del cliente este dentro de los permitidos.
func requireMSP(mspID string, permitidos ...string) error {
	for _, p := range permitidos {
		if mspID == p {
			return nil
		}
	}
	return fmt.Errorf("organizacion %s no autorizada para esta operacion", mspID)
}

func clampPageSize(pageSize int32) int32 {
	if pageSize <= 0 {
		return defaultPageSize
	}
	if pageSize > maxPageSize {
		return maxPageSize
	}
	return pageSize
}

// ──────────────────────────── Helpers de contexto ───────────────────────────

func clientMSP(ctx contractapi.TransactionContextInterface) (string, error) {
	msp, err := ctx.GetClientIdentity().GetMSPID()
	if err != nil {
		return "", fmt.Errorf("no se pudo obtener el MSP del cliente: %w", err)
	}
	return msp, nil
}

func requireReader(ctx contractapi.TransactionContextInterface) error {
	msp, err := clientMSP(ctx)
	if err != nil {
		return err
	}
	return requireMSP(msp, MSPPrescriptor, MSPMedChain, MSPPrepaga)
}

// txTimestampRFC3339 devuelve el timestamp de la transaccion (deterministico:
// viene del proposal del cliente, identico para todos los endorsers).
func txTimestampRFC3339(ctx contractapi.TransactionContextInterface) (string, error) {
	ts, err := ctx.GetStub().GetTxTimestamp()
	if err != nil {
		return "", fmt.Errorf("no se pudo obtener el timestamp de la transaccion: %w", err)
	}
	return time.Unix(ts.GetSeconds(), 0).UTC().Format(time.RFC3339), nil
}

// Las funciones del contrato devuelven string (JSON serializado a mano) en vez
// de structs: json.RawMessage dentro de un tipo de retorno confunde la
// generacion de schema de contract-api-go, y el gateway igual transporta JSON.
func (pc *PrescriptionContract) queryWithPagination(
	ctx contractapi.TransactionContextInterface,
	query string,
	pageSize int32,
	bookmark string,
) (string, error) {
	iterator, metadata, err := ctx.GetStub().GetQueryResultWithPagination(query, clampPageSize(pageSize), bookmark)
	if err != nil {
		return "", fmt.Errorf("error en query paginada: %w", err)
	}
	defer iterator.Close()

	items := []*PrescriptionAsset{}
	for iterator.HasNext() {
		result, err := iterator.Next()
		if err != nil {
			return "", err
		}
		var asset PrescriptionAsset
		if err := json.Unmarshal(result.Value, &asset); err != nil {
			continue
		}
		items = append(items, &asset)
	}
	paged := &PagedPrescriptions{
		Items:        items,
		FetchedCount: metadata.GetFetchedRecordsCount(),
		Bookmark:     metadata.GetBookmark(),
	}
	pagedBytes, err := json.Marshal(paged)
	if err != nil {
		return "", fmt.Errorf("error serializando resultado paginado: %w", err)
	}
	return string(pagedBytes), nil
}

// ─────────────────────────── Funciones del contrato ─────────────────────────

// InitLedger inicializa el chaincode (no-op en produccion).
func (pc *PrescriptionContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	fmt.Println("PrescriptionContract ledger inicializado")
	return nil
}

// CreatePrescription registra una nueva prescripcion. Solo PrescriptorMSP.
//
// canonicalJSON es el payload canonico armado por el backend:
//
//	{"clinical":{...},"created_at":"<RFC3339>","ml":{...}}
//
// con claves ordenadas alfabeticamente y sin espacios. El contrato hashea el
// string EXACTO recibido (payload_hash) y almacena clinical/ml byte a byte,
// de modo que cualquier verificador externo puede reconstruir el material y
// recomputar el hash.
//
// Idempotente: si la clave ya existe retorna error (permite reintento seguro
// con el mismo ID).
func (pc *PrescriptionContract) CreatePrescription(
	ctx contractapi.TransactionContextInterface,
	prescriptionID string,
	canonicalJSON string,
) (string, error) {
	msp, err := clientMSP(ctx)
	if err != nil {
		return "", err
	}
	if err := requireMSP(msp, MSPPrescriptor); err != nil {
		return "", err
	}
	if prescriptionID == "" {
		return "", fmt.Errorf("prescription_id vacio")
	}

	key := keyPrefix + prescriptionID
	existing, err := ctx.GetStub().GetState(key)
	if err != nil {
		return "", fmt.Errorf("error verificando existencia: %w", err)
	}
	if len(existing) > 0 {
		return "", fmt.Errorf("la prescripcion %s ya existe (idempotencia)", prescriptionID)
	}

	var payload canonicalPayload
	if err := json.Unmarshal([]byte(canonicalJSON), &payload); err != nil {
		return "", fmt.Errorf("error deserializando payload canonico: %w", err)
	}
	if len(payload.Clinical) == 0 || len(payload.ML) == 0 || payload.CreatedAt == "" {
		return "", fmt.Errorf("payload canonico incompleto: se requieren clinical, created_at y ml")
	}

	payloadHash := sha256Hex([]byte(canonicalJSON))

	asset := &PrescriptionAsset{
		DocType:          docTypePrescription,
		PrescriptionID:   prescriptionID,
		PrescriptionCode: "PRESC-" + prescriptionID,
		Estado:           EstadoPendienteAuditoria,
		Clinical:         payload.Clinical,
		ML:               payload.ML,
		CreatedAt:        payload.CreatedAt,
		CreatedByMSP:     msp,
		PayloadHash:      payloadHash,
		CurrentHash:      payloadHash,
		AuditEvents:      []AuditEvent{},
	}

	assetBytes, err := json.Marshal(asset)
	if err != nil {
		return "", fmt.Errorf("error serializando prescripcion: %w", err)
	}
	if err := ctx.GetStub().PutState(key, assetBytes); err != nil {
		return "", fmt.Errorf("error persistiendo prescripcion: %w", err)
	}
	return string(assetBytes), nil
}

// AuditPrescription registra una accion de auditoria. Solo MedChainMSP.
//
// accion: revision | aprobar | rechazar. Valida la transicion de estado,
// encadena un nuevo hash (event_hash) sobre current_hash y deja el evento
// como parte inmutable del asset.
func (pc *PrescriptionContract) AuditPrescription(
	ctx contractapi.TransactionContextInterface,
	prescriptionID string,
	accion string,
	justificacion string,
	auditor string,
) (string, error) {
	msp, err := clientMSP(ctx)
	if err != nil {
		return "", err
	}
	if err := requireMSP(msp, MSPMedChain); err != nil {
		return "", err
	}
	if auditor == "" {
		return "", fmt.Errorf("auditor vacio")
	}
	if len(justificacion) > maxJustificacion {
		return "", fmt.Errorf("justificacion supera el maximo de %d caracteres", maxJustificacion)
	}

	estadoNuevo, err := estadoPorAccion(accion)
	if err != nil {
		return "", err
	}

	key := keyPrefix + prescriptionID
	data, err := ctx.GetStub().GetState(key)
	if err != nil {
		return "", fmt.Errorf("error leyendo prescripcion: %w", err)
	}
	if len(data) == 0 {
		return "", fmt.Errorf("prescripcion %s no encontrada", prescriptionID)
	}

	var asset PrescriptionAsset
	if err := json.Unmarshal(data, &asset); err != nil {
		return "", fmt.Errorf("error deserializando prescripcion: %w", err)
	}

	if err := validarTransicion(asset.Estado, estadoNuevo); err != nil {
		return "", err
	}

	timestamp, err := txTimestampRFC3339(ctx)
	if err != nil {
		return "", err
	}

	prevHash := asset.CurrentHash
	eventHash := computeEventHash(prevHash, accion, estadoNuevo, auditor, justificacion, timestamp)

	event := AuditEvent{
		Seq:              len(asset.AuditEvents) + 1,
		Accion:           accion,
		EstadoResultante: estadoNuevo,
		Auditor:          auditor,
		Justificacion:    justificacion,
		Timestamp:        timestamp,
		TxID:             ctx.GetStub().GetTxID(),
		PrevHash:         prevHash,
		EventHash:        eventHash,
	}

	asset.AuditEvents = append(asset.AuditEvents, event)
	asset.Estado = estadoNuevo
	asset.CurrentHash = eventHash

	assetBytes, err := json.Marshal(&asset)
	if err != nil {
		return "", fmt.Errorf("error serializando prescripcion: %w", err)
	}
	if err := ctx.GetStub().PutState(key, assetBytes); err != nil {
		return "", fmt.Errorf("error persistiendo prescripcion: %w", err)
	}
	return string(assetBytes), nil
}

// GetPrescription retorna una prescripcion por su ID. Lectura: las tres orgs.
func (pc *PrescriptionContract) GetPrescription(
	ctx contractapi.TransactionContextInterface,
	prescriptionID string,
) (string, error) {
	if err := requireReader(ctx); err != nil {
		return "", err
	}
	data, err := ctx.GetStub().GetState(keyPrefix + prescriptionID)
	if err != nil {
		return "", fmt.Errorf("error leyendo prescripcion: %w", err)
	}
	if len(data) == 0 {
		return "", fmt.Errorf("prescripcion %s no encontrada", prescriptionID)
	}
	return string(data), nil
}

// ListPrescriptions lista todas las prescripciones, mas recientes primero
// (orden por prescription_id ULID descendente), con paginacion por bookmark.
func (pc *PrescriptionContract) ListPrescriptions(
	ctx contractapi.TransactionContextInterface,
	pageSize int32,
	bookmark string,
) (string, error) {
	if err := requireReader(ctx); err != nil {
		return "", err
	}
	query := `{"selector":{"docType":"prescription"},"sort":[{"docType":"desc"},{"prescription_id":"desc"}]}`
	return pc.queryWithPagination(ctx, query, pageSize, bookmark)
}

// QueryPrescriptionsByEstado lista prescripciones por estado del ciclo de
// auditoria (FIFO: mas antiguas primero). Es la cola de auditoria.
func (pc *PrescriptionContract) QueryPrescriptionsByEstado(
	ctx contractapi.TransactionContextInterface,
	estado string,
	pageSize int32,
	bookmark string,
) (string, error) {
	if err := requireReader(ctx); err != nil {
		return "", err
	}
	switch estado {
	case EstadoPendienteAuditoria, EstadoEnRevision, EstadoAprobada, EstadoRechazada:
	default:
		return "", fmt.Errorf("estado desconocido: %s", estado)
	}
	query := fmt.Sprintf(
		`{"selector":{"docType":"prescription","estado":"%s"},"sort":[{"docType":"asc"},{"estado":"asc"},{"created_at":"asc"}]}`,
		estado,
	)
	return pc.queryWithPagination(ctx, query, pageSize, bookmark)
}

// QueryPrescriptionsByPatient lista las prescripciones de un paciente
// (seudonimo patient_id), en orden cronologico.
func (pc *PrescriptionContract) QueryPrescriptionsByPatient(
	ctx contractapi.TransactionContextInterface,
	patientID string,
	pageSize int32,
	bookmark string,
) (string, error) {
	if err := requireReader(ctx); err != nil {
		return "", err
	}
	pid, err := strconv.ParseInt(patientID, 10, 64)
	if err != nil {
		return "", fmt.Errorf("patient_id invalido: %s", patientID)
	}
	query := fmt.Sprintf(
		`{"selector":{"docType":"prescription","clinical.patient_id":%d},"sort":[{"docType":"asc"},{"clinical.patient_id":"asc"},{"created_at":"asc"}]}`,
		pid,
	)
	return pc.queryWithPagination(ctx, query, pageSize, bookmark)
}

// GetPrescriptionHistory retorna el historial de transacciones de una
// prescripcion (una entrada por cada tx que modifico la clave: creacion y
// cada accion de auditoria, con su tx_id real).
func (pc *PrescriptionContract) GetPrescriptionHistory(
	ctx contractapi.TransactionContextInterface,
	prescriptionID string,
) (string, error) {
	if err := requireReader(ctx); err != nil {
		return "", err
	}
	historyIterator, err := ctx.GetStub().GetHistoryForKey(keyPrefix + prescriptionID)
	if err != nil {
		return "", fmt.Errorf("error obteniendo historial: %w", err)
	}
	defer historyIterator.Close()

	type HistoryEntry struct {
		TxID      string      `json:"tx_id"`
		Value     interface{} `json:"value"`
		Timestamp string      `json:"timestamp"`
		IsDelete  bool        `json:"is_delete"`
	}

	history := []HistoryEntry{}
	for historyIterator.HasNext() {
		modification, err := historyIterator.Next()
		if err != nil {
			return "", err
		}
		var value interface{}
		json.Unmarshal(modification.Value, &value)
		entry := HistoryEntry{
			TxID:      modification.TxId,
			Value:     value,
			Timestamp: time.Unix(modification.Timestamp.Seconds, 0).UTC().Format(time.RFC3339),
			IsDelete:  modification.IsDelete,
		}
		history = append(history, entry)
	}

	result, err := json.Marshal(history)
	if err != nil {
		return "", err
	}
	return string(result), nil
}
