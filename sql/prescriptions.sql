-- name: insert_prescription
INSERT INTO prescriptions (prescription_code, patient_sap_id, edad, sexo, peso_kg, talla_cm, superficie_corporal_m2, diagnostico_cie10, localizacion_tumor, tipo_histologico, t, n, m, estadio, msi_alta, ras_mutado, braf_v600e, linea_tratamiento, esquema, dosis_mg_m2, medico_prescriptor, matricula, estado_validacion, motivos_validacion, blockchain_tx_id, block_index)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id;

-- name: select_all_prescriptions
SELECT * FROM prescriptions ORDER BY id;

-- name: find_prescription_by_id
SELECT * FROM prescriptions WHERE id = %s;

-- name: update_prescription_validation
UPDATE prescriptions SET estado_validacion = %s, motivos_validacion = %s WHERE id = %s;
