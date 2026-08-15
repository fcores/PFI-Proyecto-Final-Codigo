-- name: insert_patient
INSERT INTO patients (credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, blockchain_tx_id, first_name_enc, last_name_enc, birth_date_enc, gender_enc, treatment_enc, first_name_bidx, last_name_bidx, birth_date_bidx)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id;

-- name: select_all_patients
SELECT id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, blockchain_tx_id, created_at, first_name_enc, last_name_enc, birth_date_enc, gender_enc, treatment_enc FROM patients ORDER BY id;

-- name: find_patient_by_id
SELECT id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, blockchain_tx_id, created_at, first_name_enc, last_name_enc, birth_date_enc, gender_enc, treatment_enc FROM patients WHERE id = %s;

-- name: search_patients_by_index
SELECT id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, blockchain_tx_id, created_at, first_name_enc, last_name_enc, birth_date_enc, gender_enc, treatment_enc FROM patients WHERE first_name_bidx = %s OR last_name_bidx = %s ORDER BY last_name, first_name LIMIT 50;

-- name: search_patients
SELECT id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, blockchain_tx_id, created_at, first_name_enc, last_name_enc, birth_date_enc, gender_enc, treatment_enc FROM patients WHERE LOWER(first_name) LIKE %s OR LOWER(last_name) LIKE %s ORDER BY last_name, first_name LIMIT 50;
