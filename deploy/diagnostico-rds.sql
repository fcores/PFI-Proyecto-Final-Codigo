-- Diagnostico de esquema de la RDS. 100% SOLO LECTURA: no modifica nada.
--
-- Uso:
--   psql "$DATABASE_URL" -f deploy/diagnostico-rds.sql > diagnostico-rds.txt 2>&1
--
-- Si se pega en pgAdmin/DBeaver, borrar las lineas que empiezan con backslash.
-- Los NOTICE/WARNING de los bloques DO $$ salen por stderr: no olvidar el 2>&1.

\pset pager off
\pset border 2
\timing off

\echo '================================================================'
\echo ' 0. ENTORNO'
\echo '================================================================'
SELECT current_database() AS base,
       current_user       AS usuario,
       current_schema()   AS esquema,
       version()          AS version_postgres;

\echo ''
\echo '================================================================'
\echo ' 1. ESTADO DE ALEMBIC  (decide si 001/002/003 ya se aplicaron)'
\echo '================================================================'
DO $$
DECLARE v text;
BEGIN
    IF to_regclass('public.alembic_version') IS NULL THEN
        RAISE NOTICE 'alembic_version: NO EXISTE -> esta base NUNCA corrio Alembic';
    ELSE
        EXECUTE 'SELECT string_agg(version_num, '', '') FROM alembic_version' INTO v;
        RAISE NOTICE 'alembic_version: EXISTE -> revision(es) = [%]', COALESCE(v, '(tabla vacia)');
    END IF;
END $$;

\echo ''
\echo '================================================================'
\echo ' 2. INVENTARIO DE TABLAS ESPERADAS'
\echo '================================================================'
SELECT t.tabla,
       CASE WHEN to_regclass('public.' || t.tabla) IS NULL
            THEN '### FALTA ###' ELSE 'existe' END AS estado
FROM (VALUES ('users'), ('monodrugs'), ('medications'), ('patients'),
             ('prescriptions'), ('ledger_blocks'), ('audit_cases'),
             ('dictamenes'), ('corrections'),
             ('phi_access_log'), ('patient_name_tokens'), ('prescription_outbox'),
             ('alembic_version')) AS t(tabla)
ORDER BY 2 DESC, 1;

\echo ''
\echo '================================================================'
\echo ' 3. CHECKLIST DE COLUMNAS QUE EL CODIGO NECESITA'
\echo '    (cualquier "### FALTA ###" = operacion que hoy tira error)'
\echo '================================================================'
WITH esperado(tabla, columna, requerido_por) AS (
    VALUES
      ('patients','first_name_enc',        'sql/patients.sql (todas las queries)'),
      ('patients','last_name_enc',         'sql/patients.sql (todas las queries)'),
      ('patients','birth_date_enc',        'sql/patients.sql (todas las queries)'),
      ('patients','gender_enc',            'sql/patients.sql (todas las queries)'),
      ('patients','treatment_enc',         'sql/patients.sql (todas las queries)'),
      ('patients','first_name_bidx',       'sql/patients.sql insert + search_by_index'),
      ('patients','last_name_bidx',        'sql/patients.sql insert + search_by_index'),
      ('patients','birth_date_bidx',       'sql/patients.sql insert_patient'),
      ('patients','provider_enc',          'Alembic 002 (hoy nunca se escribe)'),
      ('patients','provider_id_enc',       'Alembic 002 (hoy nunca se escribe)'),
      ('patients','credential_id_enc',     'Alembic 002 (hoy nunca se escribe)'),
      ('prescriptions','patient_id',       'sql/prescriptions.sql + sql/audit.sql'),
      ('prescriptions','msi',              'sql/prescriptions.sql'),
      ('prescriptions','ras',              'sql/prescriptions.sql'),
      ('prescriptions','braf_v600e',       'sql/prescriptions.sql'),
      ('prescriptions','id_regimen',       'sql/prescriptions.sql'),
      ('prescriptions','dosis_por_farmaco','sql/prescriptions.sql'),
      ('prescriptions','features_relevantes','sql/prescriptions.sql'),
      ('prescriptions','costo_por_farmaco','NUEVA: la lee AuditCasePage.jsx'),
      ('prescriptions','costo_total',      'NUEVA: la lee AuditCasePage.jsx'),
      ('prescriptions','estado_commit',    'backend/blockchain/outbox_worker.py'),
      ('prescriptions','tx_id',            'backend/blockchain/outbox_worker.py'),
      ('prescriptions','block_number',     'Alembic 003'),
      ('prescriptions','payload_hash',     'Alembic 003'),
      ('prescriptions','updated_at',       'outbox_worker.py:72,98,122 (NO EXISTE EN NINGUN LADO)'),
      ('medications','codigo',             'sql/medications.sql'),
      ('medications','monodroga',          'sql/medications.sql'),
      ('medications','laboratorio',        'sql/medications.sql'),
      ('medications','potencia_mg',        'sql/medications.sql'),
      ('medications','unidad_potencia',    'sql/medications.sql'),
      ('medications','precio',             'sql/medications.sql'),
      ('medications','via_administracion', 'sql/medications.sql'),
      ('monodrugs','codigo',               'sql/monodrugs.sql')
)
SELECT e.tabla,
       e.columna,
       CASE WHEN c.column_name IS NULL THEN '### FALTA ###'
            ELSE 'ok: ' || c.data_type END AS estado,
       e.requerido_por
FROM esperado e
LEFT JOIN information_schema.columns c
       ON c.table_schema = 'public'
      AND c.table_name   = e.tabla
      AND c.column_name  = e.columna
ORDER BY (c.column_name IS NULL) DESC, e.tabla, e.columna;

\echo ''
\echo '================================================================'
\echo ' 4. COLUMNAS LEGACY (indican si 001 o sql/migrations ya corrieron)'
\echo '================================================================'
WITH legacy(tabla, columna, significado) AS (
    VALUES
      ('patients','sap_id',               'Alembic 001 NO aplicada'),
      ('prescriptions','patient_sap_id',  'Alembic 001 NO aplicada'),
      ('prescriptions','msi_alta',        'sql/migrations/002 NO aplicada'),
      ('prescriptions','ras_mutado',      'sql/migrations/002 NO aplicada'),
      ('medications','sap_id',            'sql/migrations/003 NO aplicada'),
      ('medications','monodroga_id',      'sql/migrations/003 NO aplicada'),
      ('monodrugs','sap_id',              'sql/migrations/003 NO aplicada'),
      ('patients','tipo_empadronamiento', 'sql/migrations/003 NO aplicada'),
      ('patients','fecha_inicio',         'sql/migrations/003 NO aplicada')
)
SELECT l.tabla, l.columna,
       CASE WHEN c.column_name IS NULL THEN 'ausente (ok)'
            ELSE '### PRESENTE -> ' || l.significado || ' ###' END AS estado
FROM legacy l
LEFT JOIN information_schema.columns c
       ON c.table_schema = 'public'
      AND c.table_name   = l.tabla
      AND c.column_name  = l.columna
ORDER BY (c.column_name IS NOT NULL) DESC, l.tabla, l.columna;

\echo ''
\echo '================================================================'
\echo ' 5. COLUMNAS COMPLETAS (tipos exactos; incluye el orden de users,'
\echo '    del que depende auth_service.py:119)'
\echo '================================================================'
SELECT table_name AS tabla,
       ordinal_position AS pos,
       column_name AS columna,
       data_type AS tipo,
       COALESCE(character_maximum_length::text, '') AS largo,
       is_nullable AS nullable,
       COALESCE(column_default, '') AS por_defecto
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('users','patients','prescriptions','audit_cases',
                     'dictamenes','corrections','medications','monodrugs',
                     'ledger_blocks','phi_access_log','patient_name_tokens',
                     'prescription_outbox')
ORDER BY table_name, ordinal_position;

\echo ''
\echo '================================================================'
\echo ' 6. TIPO DE LAS COLUMNAS _bidx  (debe ser bytea)'
\echo '    crypto.blind_index() devuelve bytes -> BYTEA'
\echo '================================================================'
SELECT table_name AS tabla, column_name AS columna, data_type AS tipo,
       CASE WHEN data_type = 'bytea' THEN 'ok'
            ELSE '### ESPERADO bytea ###' END AS estado
FROM information_schema.columns
WHERE table_schema = 'public' AND column_name LIKE '%\_bidx'
ORDER BY table_name, column_name;

\echo ''
\echo '================================================================'
\echo ' 7. CONSTRAINTS'
\echo '================================================================'
SELECT c.conrelid::regclass::text AS tabla,
       c.conname AS nombre,
       CASE c.contype WHEN 'p' THEN 'PK' WHEN 'f' THEN 'FK'
                      WHEN 'u' THEN 'UNIQUE' WHEN 'c' THEN 'CHECK'
                      ELSE c.contype::text END AS tipo,
       pg_get_constraintdef(c.oid) AS definicion
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'public'
ORDER BY 1, 3, 2;

\echo ''
\echo '================================================================'
\echo ' 8. INDICES'
\echo '================================================================'
SELECT tablename AS tabla, indexname AS indice, indexdef AS definicion
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

\echo ''
\echo '================================================================'
\echo ' 9. SECUENCIAS (prescription_id_seq la usa prescription_repo)'
\echo '================================================================'
SELECT sequence_name FROM information_schema.sequences
WHERE sequence_schema = 'public' ORDER BY 1;

\echo ''
\echo '================================================================'
\echo ' 10. VOLUMEN DE DATOS Y ESTADO DEL CIFRADO PHI'
\echo '     (decide si hace falta backfill y si el UNIQUE es aplicable)'
\echo '================================================================'
DO $$
DECLARE
    total bigint; cifrados bigint; con_bidx bigint; dups bigint; n bigint;
BEGIN
    IF to_regclass('public.patients') IS NULL THEN
        RAISE NOTICE 'patients no existe';
        RETURN;
    END IF;

    EXECUTE 'SELECT count(*) FROM patients' INTO total;
    RAISE NOTICE 'patients: % filas', total;

    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='public' AND table_name='patients'
                 AND column_name='first_name_enc') THEN
        EXECUTE 'SELECT count(*) FROM patients WHERE first_name_enc IS NOT NULL' INTO cifrados;
        RAISE NOTICE 'patients con first_name_enc poblado: % de %  -> %',
            cifrados, total,
            CASE WHEN total > 0 AND cifrados = 0
                 THEN 'NINGUNA FILA CIFRADA: el cifrado nunca funciono en prod'
                 WHEN cifrados < total THEN 'PARCIAL: hace falta backfill'
                 ELSE 'completo' END;
    ELSE
        RAISE NOTICE 'patients.first_name_enc NO EXISTE -> Alembic 002 nunca se aplico';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='public' AND table_name='patients'
                 AND column_name='last_name_bidx') THEN
        EXECUTE 'SELECT count(*) FROM patients WHERE last_name_bidx IS NOT NULL' INTO con_bidx;
        RAISE NOTICE 'patients con last_name_bidx poblado: % de %  (las filas sin bidx quedan invisibles para la busqueda por indice ciego)',
            con_bidx, total;
        EXECUTE '
            SELECT count(*) FROM (
                SELECT 1 FROM patients
                WHERE last_name_bidx IS NOT NULL
                GROUP BY last_name_bidx, first_name_bidx, birth_date_bidx
                HAVING count(*) > 1) d' INTO dups;
        RAISE NOTICE 'grupos duplicados por (last,first,dob) bidx: %  -> %',
            dups,
            CASE WHEN dups > 0 THEN 'BLOQUEA la creacion de uq_patients_name_dob_bidx'
                 ELSE 'ok, el UNIQUE se puede crear' END;
    END IF;

    IF to_regclass('public.prescriptions') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM prescriptions' INTO n;
        RAISE NOTICE 'prescriptions: % filas', n;
    END IF;

    IF to_regclass('public.audit_cases') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM audit_cases' INTO n;
        RAISE NOTICE 'audit_cases: % filas', n;
    END IF;

    IF to_regclass('public.corrections') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM corrections' INTO n;
        RAISE NOTICE 'corrections: % filas', n;
        EXECUTE 'SELECT count(*) FROM corrections WHERE valor_anterior = ''''' INTO n;
        RAISE NOTICE 'corrections con valor_anterior vacio: %  (bug de audit_router.py:64)', n;
    END IF;

    IF to_regclass('public.prescription_outbox') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM prescription_outbox' INTO n;
        RAISE NOTICE 'prescription_outbox: % filas', n;
    END IF;
END $$;

\echo ''
\echo '================================================================'
\echo ' 11. DUPLICADOS EN TEXTO PLANO (proxy del UNIQUE si no hay bidx)'
\echo '================================================================'
SELECT lower(trim(last_name))  AS apellido,
       lower(trim(first_name)) AS nombre,
       birth_date,
       count(*) AS repeticiones
FROM patients
GROUP BY 1, 2, 3
HAVING count(*) > 1
ORDER BY 4 DESC
LIMIT 50;

\echo ''
\echo '=== FIN DEL DIAGNOSTICO ==='
