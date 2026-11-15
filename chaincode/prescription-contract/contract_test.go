package main

import (
	"encoding/json"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

// La tabla de transiciones y los vectores de hash de este archivo estan
// espejados en el backend Python (tests/test_canonical_hash.py y
// tests/fakes/fake_fabric_gateway.py). Si algo cambia aca, actualizar alla.

func TestValidarTransicionPermitidas(t *testing.T) {
	casos := []struct{ actual, nueva string }{
		{EstadoPendienteAuditoria, EstadoEnRevision},
		{EstadoPendienteAuditoria, EstadoAprobada},
		{EstadoPendienteAuditoria, EstadoRechazada},
		{EstadoEnRevision, EstadoAprobada},
		{EstadoEnRevision, EstadoRechazada},
	}
	for _, c := range casos {
		if err := validarTransicion(c.actual, c.nueva); err != nil {
			t.Errorf("transicion %s -> %s deberia ser valida: %v", c.actual, c.nueva, err)
		}
	}
}

func TestValidarTransicionRechazadas(t *testing.T) {
	casos := []struct{ actual, nueva string }{
		{EstadoAprobada, EstadoRechazada},
		{EstadoAprobada, EstadoEnRevision},
		{EstadoAprobada, EstadoPendienteAuditoria},
		{EstadoRechazada, EstadoAprobada},
		{EstadoRechazada, EstadoEnRevision},
		{EstadoEnRevision, EstadoPendienteAuditoria},
		{EstadoEnRevision, EstadoEnRevision},
		{EstadoPendienteAuditoria, EstadoPendienteAuditoria},
		{"CUALQUIERA", EstadoAprobada},
	}
	for _, c := range casos {
		if err := validarTransicion(c.actual, c.nueva); err == nil {
			t.Errorf("transicion %s -> %s deberia ser invalida", c.actual, c.nueva)
		}
	}
}

func TestEstadoPorAccion(t *testing.T) {
	casos := map[string]string{
		AccionRevision: EstadoEnRevision,
		AccionAprobar:  EstadoAprobada,
		AccionRechazar: EstadoRechazada,
	}
	for accion, esperado := range casos {
		estado, err := estadoPorAccion(accion)
		if err != nil {
			t.Fatalf("accion %s: error inesperado %v", accion, err)
		}
		if estado != esperado {
			t.Errorf("accion %s: esperado %s, obtenido %s", accion, esperado, estado)
		}
	}
	if _, err := estadoPorAccion("corregir"); err == nil {
		t.Error("accion desconocida deberia dar error")
	}
}

// Vector compartido con el backend Python (tests/test_canonical_hash.py):
// el JSON canonico conocido debe producir exactamente este SHA-256.
func TestPayloadHashVectorCompartido(t *testing.T) {
	canonical := `{"clinical":{"a":1},"created_at":"2026-01-01T00:00:00Z","ml":{"b":2}}`
	esperado := "4812d96106eb7f21fd0da9b6fafcf23b5cb3dba5964e95feb93970898f97ebc4"
	if got := sha256Hex([]byte(canonical)); got != esperado {
		t.Errorf("payload_hash del vector compartido: esperado %s, obtenido %s", esperado, got)
	}
}

// Vector compartido con el backend Python: mismo eslabon de auditoria, mismo hash.
func TestComputeEventHashVectorCompartido(t *testing.T) {
	prev := strings.Repeat("0", 64)
	esperado := "92254dfc8a7257b357b95c7564f9e12d4eabfa7b21453203ed4b2a87e3218b5f"
	got := computeEventHash(prev, AccionAprobar, EstadoAprobada, "auditor1", "Cumple guias clinicas", "2026-01-01T00:00:00Z")
	if got != esperado {
		t.Errorf("event_hash del vector compartido: esperado %s, obtenido %s", esperado, got)
	}
}

func TestComputeEventHashEncadena(t *testing.T) {
	h1 := computeEventHash(strings.Repeat("0", 64), AccionRevision, EstadoEnRevision, "aud", "pedir estudios", "2026-01-01T00:00:00Z")
	h2 := computeEventHash(h1, AccionAprobar, EstadoAprobada, "aud", "ok", "2026-01-02T00:00:00Z")
	if h1 == h2 {
		t.Error("eslabones distintos no pueden producir el mismo hash")
	}
	// Determinismo: mismos insumos, mismo hash.
	if h2 != computeEventHash(h1, AccionAprobar, EstadoAprobada, "aud", "ok", "2026-01-02T00:00:00Z") {
		t.Error("computeEventHash no es deterministico")
	}
}

func TestRequireMSP(t *testing.T) {
	if err := requireMSP(MSPPrescriptor, MSPPrescriptor); err != nil {
		t.Errorf("PrescriptorMSP deberia estar autorizado: %v", err)
	}
	if err := requireMSP(MSPPrepaga, MSPPrescriptor, MSPMedChain, MSPPrepaga); err != nil {
		t.Errorf("PrepagaMSP deberia poder leer: %v", err)
	}
	if err := requireMSP(MSPPrescriptor, MSPMedChain); err == nil {
		t.Error("PrescriptorMSP no deberia poder auditar")
	}
	if err := requireMSP("IntrusoMSP", MSPPrescriptor, MSPMedChain, MSPPrepaga); err == nil {
		t.Error("un MSP desconocido no deberia estar autorizado")
	}
}

func TestClampPageSize(t *testing.T) {
	if clampPageSize(0) != defaultPageSize {
		t.Error("pageSize 0 deberia usar el default")
	}
	if clampPageSize(-5) != defaultPageSize {
		t.Error("pageSize negativo deberia usar el default")
	}
	if clampPageSize(10) != 10 {
		t.Error("pageSize valido deberia respetarse")
	}
	if clampPageSize(10000) != maxPageSize {
		t.Error("pageSize excesivo deberia acotarse al maximo")
	}
}

// Guard-rail de determinismo: con endorsement AND de 3 orgs, cualquier fuente
// local de tiempo produce write-sets distintos por endorser y la transaccion
// falla por ENDORSEMENT_POLICY_FAILURE. Los timestamps deben salir de
// GetTxTimestamp() o del payload firmado.
// Se parsea el AST en vez de buscar la cadena "time.Now(" en el fuente: el
// propio contract.go documenta la regla en un comentario, y un strings.Contains
// matchea ese comentario y falla siempre (falso positivo).
func TestSinTimeNowEnElContrato(t *testing.T) {
	fset := token.NewFileSet()
	archivo, err := parser.ParseFile(fset, "contract.go", nil, 0)
	if err != nil {
		t.Fatalf("no se pudo parsear contract.go: %v", err)
	}

	ast.Inspect(archivo, func(n ast.Node) bool {
		call, ok := n.(*ast.CallExpr)
		if !ok {
			return true
		}
		sel, ok := call.Fun.(*ast.SelectorExpr)
		if !ok || sel.Sel.Name != "Now" {
			return true
		}
		if pkg, ok := sel.X.(*ast.Ident); ok && pkg.Name == "time" {
			t.Errorf("%s: contract.go llama time.Now(): fuente de no-determinismo "+
				"prohibida en chaincode (usar GetTxTimestamp)",
				fset.Position(call.Pos()))
		}
		return true
	})
}

const indexDir = "META-INF/statedb/couchdb/indexes"

var (
	reSort  = regexp.MustCompile(`"sort":\[(.*?)\]`)
	reCampo = regexp.MustCompile(`"([^"]+)":"(?:asc|desc)"`)
)

// Guard-rail de rich queries: CouchDB/Mango rechaza en RUNTIME cualquier query
// con "sort" que no tenga un indice que cubra exactamente esos campos, en ese
// orden ("No index exists for this sort, try indexing by the sort fields").
// El chaincode compila y los tests unitarios pasan igual, asi que sin este test
// la falta de un indice recien aparece en la cola de auditoria ya desplegada.
func TestRichQueriesTienenIndiceCouchDB(t *testing.T) {
	src, err := os.ReadFile("contract.go")
	if err != nil {
		t.Fatalf("no se pudo leer contract.go: %v", err)
	}

	archivos, err := filepath.Glob(filepath.Join(indexDir, "*.json"))
	if err != nil {
		t.Fatalf("no se pudo listar %s: %v", indexDir, err)
	}

	indices := make(map[string]string) // "campo1|campo2" -> archivo
	for _, ruta := range archivos {
		raw, err := os.ReadFile(ruta)
		if err != nil {
			t.Fatalf("no se pudo leer %s: %v", ruta, err)
		}
		var idx struct {
			Index struct {
				Fields []string `json:"fields"`
			} `json:"index"`
		}
		if err := json.Unmarshal(raw, &idx); err != nil {
			t.Fatalf("%s no es JSON valido: %v", ruta, err)
		}
		if len(idx.Index.Fields) == 0 {
			t.Errorf("%s no declara index.fields", ruta)
			continue
		}
		indices[strings.Join(idx.Index.Fields, "|")] = ruta
	}

	sorts := reSort.FindAllStringSubmatch(string(src), -1)
	if len(sorts) == 0 {
		t.Fatal("no se encontro ningun \"sort\" en contract.go: revisar este test")
	}

	for _, s := range sorts {
		var campos []string
		for _, c := range reCampo.FindAllStringSubmatch(s[1], -1) {
			campos = append(campos, c[1])
		}
		clave := strings.Join(campos, "|")
		if _, ok := indices[clave]; !ok {
			t.Errorf("el sort por %v no tiene indice en %s; agregar un .json con "+
				"index.fields = %v o la query falla en runtime contra CouchDB",
				campos, indexDir, campos)
		}
	}
}
