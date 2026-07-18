-- name: insert_patient
INSERT INTO patients (sap_id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, tipo_empadronamiento, fecha_inicio, fecha_primera_toma, cadencia_estimada_toma, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, blockchain_tx_id)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id;

-- name: select_all_patients
SELECT * FROM patients ORDER BY id;
