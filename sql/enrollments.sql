-- name: insert_enrollment
INSERT INTO enrollments (enrollment_code, tipo, diagnostico, medications)
VALUES (%s, %s, %s, %s)
RETURNING id;

-- name: select_enrollments_by_tipo
SELECT * FROM enrollments WHERE tipo = %s ORDER BY id;
