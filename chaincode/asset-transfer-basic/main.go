// Punto de entrada del chaincode asset-transfer-basic.
// Registra el smart contract y arranca el proceso del chaincode.
package main

import (
	"log"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
	"github.com/pfi/asset-transfer-basic/chaincode"
)

func main() {
	cc, err := contractapi.NewChaincode(&chaincode.SmartContract{})
	if err != nil {
		log.Panicf("Error creando el chaincode asset-transfer-basic: %v", err)
	}

	if err := cc.Start(); err != nil {
		log.Panicf("Error iniciando el chaincode asset-transfer-basic: %v", err)
	}
}
