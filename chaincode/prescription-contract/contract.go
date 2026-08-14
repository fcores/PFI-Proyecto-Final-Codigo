// Package main implementa el chaincode PrescriptionContract para prescripciones
// oncologicas con modelo append-only. Las correcciones y dictamenes son eventos
// nuevos, nunca sobrescritura del estado original.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// PrescriptionContract gestiona prescripciones en Hyperledger Fabric.
type PrescriptionContract struct {
	contractapi.Contract
}

// Prescription representa el registro on-chain de una prescripcion.
// No contiene PHI identificatoria: patient_id es un seudonimo.
type Prescription struct {
	DocType              string  `json:"docType"`
	PrescriptionID       int64   `json:"prescription_id"`
	PrescriptionCode     string  `json:"prescription_code"`
	PatientID            int64   `json:"patient_id"`
	DiagnosticoCIE10     string  `json:"diagnostico_cie10"`
	Estadio              string  `json:"estadio"`
	IDRegimen            string  `json:"id_regimen"`
	Esquema              string  `json:"esquema"`
	DosisMgM2            float64 `json:"dosis_mg_m2"`
	EstadoValidacion     string  `json:"estado_validacion"`
	ProbConcordante      float64 `json:"probabilidad_concordante"`
	OrigenValidacion     string  `json:"origen_validacion"`
	VersionModelo        string  `json:"version_modelo"`
	MedicoPrescriptor    string  `json:"medico_prescriptor"`
	Matricula            string  `json:"matricula"`
	PayloadHash          string  `json:"payload_hash"`
	CreatedAt            string  `json:"created_at"`
}

// DictamenEvent representa un dictamen emitido sobre una prescripcion.
type DictamenEvent struct {
	DocType        string `json:"docType"`
	PrescriptionID int64  `json:"prescription_id"`
	Resultado      string `json:"resultado"`
	Justificacion  string `json:"justificacion"`
	Auditor        string `json:"auditor"`
	CreatedAt      string `json:"created_at"`
}

// CorrectionEvent representa una correccion sobre un caso de auditoria.
type CorrectionEvent struct {
	DocType        string `json:"docType"`
	PrescriptionID int64  `json:"prescription_id"`
	Campo          string `json:"campo"`
	ValorAnterior  string `json:"valor_anterior"`
	ValorNuevo     string `json:"valor_nuevo"`
	Justificacion  string `json:"justificacion"`
	Auditor        string `json:"auditor"`
	CreatedAt      string `json:"created_at"`
}

// InitLedger inicializa el chaincode (no-op en produccion).
func (pc *PrescriptionContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	fmt.Println("PrescriptionContract ledger inicializado")
	return nil
}

// CreatePrescription registra una nueva prescripcion en el world state.
// Es idempotente: si la clave ya existe retorna error (permite reintento seguro).
func (pc *PrescriptionContract) CreatePrescription(ctx contractapi.TransactionContextInterface, prescriptionJSON string) error {
	var presc Prescription
	if err := json.Unmarshal([]byte(prescriptionJSON), &presc); err != nil {
		return fmt.Errorf("error deserializando prescripcion: %w", err)
	}

	presc.DocType = "prescription"
	if presc.CreatedAt == "" {
		presc.CreatedAt = time.Now().UTC().Format(time.RFC3339)
	}

	key := fmt.Sprintf("PRESC_%d", presc.PrescriptionID)

	existing, err := ctx.GetStub().GetState(key)
	if err != nil {
		return fmt.Errorf("error verificando existencia: %w", err)
	}
	if existing != nil {
		return fmt.Errorf("prescripcion %d ya existe (idempotencia)", presc.PrescriptionID)
	}

	// Calcular hash de integridad del payload completo
	payloadBytes, _ := json.Marshal(presc)
	hash := sha256.Sum256(payloadBytes)
	presc.PayloadHash = hex.EncodeToString(hash[:])

	finalBytes, err := json.Marshal(presc)
	if err != nil {
		return fmt.Errorf("error serializando prescripcion: %w", err)
	}

	return ctx.GetStub().PutState(key, finalBytes)
}

// GetPrescription retorna una prescripcion por su ID.
func (pc *PrescriptionContract) GetPrescription(ctx contractapi.TransactionContextInterface, prescriptionID int64) (*Prescription, error) {
	key := fmt.Sprintf("PRESC_%d", prescriptionID)
	data, err := ctx.GetStub().GetState(key)
	if err != nil {
		return nil, fmt.Errorf("error leyendo prescripcion: %w", err)
	}
	if data == nil {
		return nil, fmt.Errorf("prescripcion %d no encontrada", prescriptionID)
	}

	var presc Prescription
	if err := json.Unmarshal(data, &presc); err != nil {
		return nil, fmt.Errorf("error deserializando: %w", err)
	}
	return &presc, nil
}

// QueryPrescriptionsByPatient busca prescripciones por patient_id usando rich query (CouchDB).
func (pc *PrescriptionContract) QueryPrescriptionsByPatient(ctx contractapi.TransactionContextInterface, patientID int64) ([]*Prescription, error) {
	queryString := fmt.Sprintf(`{"selector":{"docType":"prescription","patient_id":%d}}`, patientID)
	resultsIterator, err := ctx.GetStub().GetQueryResult(queryString)
	if err != nil {
		return nil, fmt.Errorf("error en query: %w", err)
	}
	defer resultsIterator.Close()

	var prescriptions []*Prescription
	for resultsIterator.HasNext() {
		queryResult, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}
		var presc Prescription
		if err := json.Unmarshal(queryResult.Value, &presc); err != nil {
			continue
		}
		prescriptions = append(prescriptions, &presc)
	}
	return prescriptions, nil
}

// AppendDictamen registra un dictamen como evento append-only.
func (pc *PrescriptionContract) AppendDictamen(ctx contractapi.TransactionContextInterface, dictamenJSON string) error {
	var dictamen DictamenEvent
	if err := json.Unmarshal([]byte(dictamenJSON), &dictamen); err != nil {
		return fmt.Errorf("error deserializando dictamen: %w", err)
	}

	dictamen.DocType = "dictamen"
	if dictamen.CreatedAt == "" {
		dictamen.CreatedAt = time.Now().UTC().Format(time.RFC3339)
	}

	// Verificar que la prescripcion existe
	prescKey := fmt.Sprintf("PRESC_%d", dictamen.PrescriptionID)
	existing, err := ctx.GetStub().GetState(prescKey)
	if err != nil || existing == nil {
		return fmt.Errorf("prescripcion %d no encontrada para dictamen", dictamen.PrescriptionID)
	}

	key := fmt.Sprintf("DICT_%d_%s", dictamen.PrescriptionID, dictamen.CreatedAt)
	data, err := json.Marshal(dictamen)
	if err != nil {
		return fmt.Errorf("error serializando dictamen: %w", err)
	}

	return ctx.GetStub().PutState(key, data)
}

// AppendCorrection registra una correccion como evento append-only.
func (pc *PrescriptionContract) AppendCorrection(ctx contractapi.TransactionContextInterface, correctionJSON string) error {
	var correction CorrectionEvent
	if err := json.Unmarshal([]byte(correctionJSON), &correction); err != nil {
		return fmt.Errorf("error deserializando correccion: %w", err)
	}

	correction.DocType = "correction"
	if correction.CreatedAt == "" {
		correction.CreatedAt = time.Now().UTC().Format(time.RFC3339)
	}

	prescKey := fmt.Sprintf("PRESC_%d", correction.PrescriptionID)
	existing, err := ctx.GetStub().GetState(prescKey)
	if err != nil || existing == nil {
		return fmt.Errorf("prescripcion %d no encontrada para correccion", correction.PrescriptionID)
	}

	key := fmt.Sprintf("CORR_%d_%s_%s", correction.PrescriptionID, correction.Campo, correction.CreatedAt)
	data, err := json.Marshal(correction)
	if err != nil {
		return fmt.Errorf("error serializando correccion: %w", err)
	}

	return ctx.GetStub().PutState(key, data)
}

// GetPrescriptionHistory retorna el historial de transacciones de una prescripcion.
func (pc *PrescriptionContract) GetPrescriptionHistory(ctx contractapi.TransactionContextInterface, prescriptionID int64) (string, error) {
	key := fmt.Sprintf("PRESC_%d", prescriptionID)
	historyIterator, err := ctx.GetStub().GetHistoryForKey(key)
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

	var history []HistoryEntry
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
