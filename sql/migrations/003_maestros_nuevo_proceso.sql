ALTER TABLE monodrugs ADD COLUMN IF NOT EXISTS codigo VARCHAR(100);
ALTER TABLE monodrugs DROP COLUMN IF EXISTS sap_id;

ALTER TABLE medications ADD COLUMN IF NOT EXISTS codigo VARCHAR(100);
ALTER TABLE medications ADD COLUMN IF NOT EXISTS laboratorio VARCHAR(300);
ALTER TABLE medications ADD COLUMN IF NOT EXISTS unidad_potencia VARCHAR(50);
ALTER TABLE medications ADD COLUMN IF NOT EXISTS monodroga VARCHAR(200);

UPDATE medications SET monodroga = monodroga_id WHERE monodroga IS NULL;

ALTER TABLE medications DROP COLUMN IF EXISTS sap_id;
ALTER TABLE medications DROP COLUMN IF EXISTS monodroga_id;

ALTER TABLE patients DROP COLUMN IF EXISTS tipo_empadronamiento;
ALTER TABLE patients DROP COLUMN IF EXISTS fecha_inicio;
ALTER TABLE patients DROP COLUMN IF EXISTS fecha_primera_toma;
ALTER TABLE patients DROP COLUMN IF EXISTS cadencia_estimada_toma;

DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS agreements;
