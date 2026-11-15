-- name: insert_patient
INSERT INTO patients (credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, first_name_enc, last_name_enc, birth_date_enc, gender_enc, provider_enc, provider_id_enc, credential_id_enc, treatment_enc, first_name_bidx, last_name_bidx, birth_date_bidx)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id;

-- name: select_all_patients
SELECT id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, created_at, first_name_enc, last_name_enc, birth_date_enc, gender_enc, provider_enc, provider_id_enc, credential_id_enc, treatment_enc FROM patients ORDER BY id LIMIT %s OFFSET %s;

-- name: find_patient_by_id
SELECT id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, created_at, first_name_enc, last_name_enc, birth_date_enc, gender_enc, provider_enc, provider_id_enc, credential_id_enc, treatment_enc FROM patients WHERE id = %s;

-- name: search_patients_by_index
SELECT id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, created_at, first_name_enc, last_name_enc, birth_date_enc, gender_enc, provider_enc, provider_id_enc, credential_id_enc, treatment_enc FROM patients WHERE first_name_bidx = %s OR last_name_bidx = %s ORDER BY last_name, first_name LIMIT 50;

-- name: search_patients
SELECT id, credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment, medications, hc_filename, ap_filename, img_filename, lab_filename, receta_filename, otros_filename, created_at, first_name_enc, last_name_enc, birth_date_enc, gender_enc, provider_enc, provider_id_enc, credential_id_enc, treatment_enc FROM patients WHERE LOWER(first_name) LIKE %s OR LOWER(last_name) LIKE %s ORDER BY last_name, first_name LIMIT 50;

-- name: insert_phi_access_log
INSERT INTO phi_access_log (user_id, username, patient_id, action, fields_accessed)
VALUES (%s, %s, %s, %s, %s);

-- name: insert_name_token
INSERT INTO patient_name_tokens (patient_id, token_bidx) VALUES (%s, %s);

-- name: delete_name_tokens
DELETE FROM patient_name_tokens WHERE patient_id = %s;

-- name: search_patients_by_token
SELECT DISTINCT p.id, p.credential_id, p.provider_id, p.provider, p.first_name, p.last_name, p.birth_date, p.gender, p.treatment, p.medications, p.hc_filename, p.ap_filename, p.img_filename, p.lab_filename, p.receta_filename, p.otros_filename, p.created_at, p.first_name_enc, p.last_name_enc, p.birth_date_enc, p.gender_enc, p.provider_enc, p.provider_id_enc, p.credential_id_enc, p.treatment_enc
FROM patients p
JOIN patient_name_tokens t ON t.patient_id = p.id
WHERE t.token_bidx = %s
ORDER BY p.last_name, p.first_name
LIMIT 50;

-- name: patient_exists
SELECT 1 FROM patients WHERE id = %s;

-- name: anonymize_patient
UPDATE patients SET
    credential_id = NULL, provider_id = NULL, provider = NULL,
    first_name = '***', last_name = '***', birth_date = DATE '1900-01-01', gender = '***',
    treatment = NULL, medications = '[]',
    hc_filename = NULL, ap_filename = NULL, img_filename = NULL,
    lab_filename = NULL, receta_filename = NULL, otros_filename = NULL,
    first_name_enc = NULL, last_name_enc = NULL, birth_date_enc = NULL, gender_enc = NULL,
    provider_enc = NULL, provider_id_enc = NULL, credential_id_enc = NULL, treatment_enc = NULL,
    first_name_bidx = NULL, last_name_bidx = NULL, birth_date_bidx = NULL,
    anonymized_at = NOW()
WHERE id = %s
RETURNING id;
