-- name: insert_audit_case
INSERT INTO audit_cases (prescription_id, status) VALUES (%s, %s) RETURNING id;

-- name: select_pending_cases
SELECT ac.*, p.prescription_code, p.patient_sap_id, p.diagnostico_cie10, p.estadio, p.esquema, p.estado_validacion, p.created_at AS prescription_created_at
FROM audit_cases ac
JOIN prescriptions p ON ac.prescription_id = p.id
WHERE ac.status IN ('pendiente', 'en_revision')
ORDER BY ac.created_at;

-- name: find_audit_case_by_id
SELECT ac.*, p.prescription_code, p.patient_sap_id, p.diagnostico_cie10, p.estadio, p.esquema, p.estado_validacion, p.motivos_validacion, p.created_at AS prescription_created_at
FROM audit_cases ac
JOIN prescriptions p ON ac.prescription_id = p.id
WHERE ac.id = %s;

-- name: update_audit_case_status
UPDATE audit_cases SET status = %s, assigned_auditor = %s WHERE id = %s;

-- name: insert_dictamen
INSERT INTO dictamenes (audit_case_id, resultado, justificacion, auditor_username, blockchain_tx_id)
VALUES (%s, %s, %s, %s, %s)
RETURNING id;

-- name: insert_correction
INSERT INTO corrections (audit_case_id, campo, valor_anterior, valor_nuevo, justificacion, auditor_username, blockchain_tx_id)
VALUES (%s, %s, %s, %s, %s, %s, %s)
RETURNING id;

-- name: select_corrections_by_case
SELECT * FROM corrections WHERE audit_case_id = %s ORDER BY created_at;

-- name: select_dictamen_by_case
SELECT * FROM dictamenes WHERE audit_case_id = %s ORDER BY created_at DESC LIMIT 1;
