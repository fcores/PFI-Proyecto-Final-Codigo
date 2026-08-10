-- name: insert_monodrug
INSERT INTO monodrugs (descripcion, codigo) VALUES (%s, %s) RETURNING id;

-- name: select_all_monodrugs
SELECT * FROM monodrugs ORDER BY id;

-- name: find_monodrug_by_descripcion
SELECT * FROM monodrugs WHERE LOWER(descripcion) = LOWER(%s) LIMIT 1;
