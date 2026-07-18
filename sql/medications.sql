-- name: insert_medication
INSERT INTO medications (descripcion, ean, codigo_alfabeta, tipo_conservacion, sap_id, monodroga_id, tamano_dimension)
VALUES (%s, %s, %s, %s, %s, %s, %s)
RETURNING id;

-- name: select_all_medications
SELECT * FROM medications ORDER BY id;
