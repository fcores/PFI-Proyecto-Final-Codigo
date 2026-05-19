package main

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type PatientContract struct {
	contractapi.Contract
}

type Patient struct {
	DocType              string `json:"docType"`
	PatientID            string `json:"patientId"`
	SapID                string `json:"sapId"`
	FirstName            string `json:"firstName"`
	LastName             string `json:"lastName"`
	BirthDate            string `json:"birthDate"`
	Gender               string `json:"gender"`
	TipoEmpadronamiento string `json:"tipoEmpadronamiento"`
	FechaInicio          string `json:"fechaInicio"`
	DataHash             string `json:"dataHash"`
	CreatedAt            string `json:"createdAt"`
}

func (pc *PatientContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	fmt.Println("Patient ledger initialized")
	return nil
}

func (pc *PatientContract) CreatePatient(ctx contractapi.TransactionContextInterface, patientID string, dataJSON string) (string, error) {
	key := "PATIENT_" + patientID

	existing, err := ctx.GetStub().GetState(key)
	if err != nil {
		return "", fmt.Errorf("failed to read state: %v", err)
	}
	if existing != nil && len(existing) > 0 {
		return "", fmt.Errorf("patient %s already exists", patientID)
	}

	var patient Patient
	if err := json.Unmarshal([]byte(dataJSON), &patient); err != nil {
		return "", fmt.Errorf("failed to parse patient data: %v", err)
	}
	patient.DocType = "patient"
	patient.PatientID = patientID
	patient.CreatedAt = time.Now().UTC().Format(time.RFC3339)

	patientBytes, err := json.Marshal(patient)
	if err != nil {
		return "", fmt.Errorf("failed to marshal patient: %v", err)
	}

	if err := ctx.GetStub().PutState(key, patientBytes); err != nil {
		return "", fmt.Errorf("failed to put state: %v", err)
	}

	return string(patientBytes), nil
}

func (pc *PatientContract) QueryPatient(ctx contractapi.TransactionContextInterface, patientID string) (string, error) {
	key := "PATIENT_" + patientID
	data, err := ctx.GetStub().GetState(key)
	if err != nil {
		return "", fmt.Errorf("failed to read state: %v", err)
	}
	if data == nil || len(data) == 0 {
		return "", fmt.Errorf("patient %s not found", patientID)
	}
	return string(data), nil
}

func (pc *PatientContract) GetPatientHistory(ctx contractapi.TransactionContextInterface, patientID string) (string, error) {
	key := "PATIENT_" + patientID
	iterator, err := ctx.GetStub().GetHistoryForKey(key)
	if err != nil {
		return "", fmt.Errorf("failed to get history: %v", err)
	}
	defer iterator.Close()

	var history []map[string]interface{}
	for iterator.HasNext() {
		res, err := iterator.Next()
		if err != nil {
			return "", fmt.Errorf("failed to iterate: %v", err)
		}
		entry := map[string]interface{}{
			"txId":      res.TxId,
			"timestamp": res.Timestamp,
			"isDelete":  res.IsDelete,
		}
		if !res.IsDelete {
			var val interface{}
			json.Unmarshal(res.Value, &val)
			entry["value"] = val
		}
		history = append(history, entry)
	}

	historyBytes, _ := json.Marshal(history)
	return string(historyBytes), nil
}

func main() {
	chaincode, err := contractapi.NewChaincode(&PatientContract{})
	if err != nil {
		fmt.Printf("Error creating chaincode: %v\n", err)
		return
	}
	if err := chaincode.Start(); err != nil {
		fmt.Printf("Error starting chaincode: %v\n", err)
	}
}
