-- name: insert_agreement
INSERT INTO agreements (laboratorio, prestador, medicamento, medicamento_sap, medico_auditor, fecha_inicio, fecha_fin, condicion_recupero, contrato_filename)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id;

-- name: select_all_agreements
SELECT * FROM agreements ORDER BY id;
