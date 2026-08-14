-- name: insert_patient
INSERT INTO patients (credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, blockchain_tx_id)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id;

-- name: select_all_patients
SELECT id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, blockchain_tx_id, created_at FROM patients ORDER BY id;

-- name: find_patient_by_id
SELECT id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, blockchain_tx_id, created_at FROM patients WHERE id = %s;

-- name: search_patients
SELECT id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, blockchain_tx_id, created_at FROM patients WHERE LOWER(first_name) LIKE %s OR LOWER(last_name) LIKE %s ORDER BY last_name, first_name LIMIT 50;
