-- name: insert_prescription
INSERT INTO prescriptions (
    prescription_code, patient_sap_id, edad, sexo, peso_kg, talla_cm, superficie_corporal_m2,
    diagnostico_cie10, localizacion_tumor, tipo_histologico, t, n, m, estadio,
    msi, ras, braf_v600e, linea_tratamiento, id_regimen, esquema, dosis_por_farmaco, dosis_mg_m2,
    medico_prescriptor, matricula, estado_validacion, motivos_validacion,
    probabilidad_concordante, nivel_confianza, umbral_bajo, umbral_alto,
    origen_validacion, version_modelo, features_relevantes,
    blockchain_tx_id, block_index
)
VALUES (
    %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s, %s,
    %s, %s
)
RETURNING id;

-- name: select_all_prescriptions
SELECT * FROM prescriptions ORDER BY id;
