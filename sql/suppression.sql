-- name: insert_request
INSERT INTO patient_suppression_requests (patient_id, requested_by, motivo, ejecutable_desde)
VALUES (%s, %s, %s, %s)
RETURNING id, patient_id, requested_by, motivo, requested_at, ejecutable_desde, executed_at, estado;

-- name: list_requests
SELECT id, patient_id, requested_by, motivo, requested_at, ejecutable_desde, executed_at, estado
FROM patient_suppression_requests
ORDER BY requested_at DESC;

-- name: list_due_requests
SELECT id, patient_id, requested_by, motivo, requested_at, ejecutable_desde, executed_at, estado
FROM patient_suppression_requests
WHERE estado = 'pendiente' AND ejecutable_desde <= %s
ORDER BY ejecutable_desde;

-- name: find_pending_by_patient
SELECT id, patient_id, requested_by, motivo, requested_at, ejecutable_desde, executed_at, estado
FROM patient_suppression_requests
WHERE patient_id = %s AND estado = 'pendiente';

-- name: mark_executed
UPDATE patient_suppression_requests SET estado = 'ejecutada', executed_at = NOW()
WHERE id = %s
RETURNING id, patient_id, requested_by, motivo, requested_at, ejecutable_desde, executed_at, estado;
