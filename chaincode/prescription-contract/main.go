package main

import (
	"log"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

func main() {
	chaincode, err := contractapi.NewChaincode(&PrescriptionContract{})
	if err != nil {
		log.Fatalf("Error creando chaincode de prescripciones: %v", err)
	}
	if err := chaincode.Start(); err != nil {
		log.Fatalf("Error iniciando chaincode de prescripciones: %v", err)
	}
}
