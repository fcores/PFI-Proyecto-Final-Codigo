-- name: insert_monodrug
INSERT INTO monodrugs (descripcion, sap_id) VALUES (%s, %s) RETURNING id;

-- name: select_all_monodrugs
SELECT * FROM monodrugs ORDER BY id;

-- name: find_monodrug_by_sap_id
SELECT * FROM monodrugs WHERE sap_id = %s LIMIT 1;
