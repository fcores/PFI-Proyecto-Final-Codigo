-- name: insert_medication
INSERT INTO medications (codigo, descripcion, ean, codigo_alfabeta, tipo_conservacion, laboratorio, monodroga, tamano_dimension, potencia_mg, unidad_potencia, precio, via_administracion)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id;

-- name: select_all_medications
SELECT * FROM medications ORDER BY id;

-- name: select_medications_by_monodroga
SELECT * FROM medications
WHERE LOWER(monodroga) = LOWER(%s)
ORDER BY potencia_mg NULLS LAST, id;
