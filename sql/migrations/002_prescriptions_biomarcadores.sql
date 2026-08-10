ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS msi VARCHAR(20);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS ras VARCHAR(20);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS id_regimen VARCHAR(10);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS dosis_por_farmaco TEXT DEFAULT '[]';
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS probabilidad_concordante NUMERIC(10,6);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS nivel_confianza VARCHAR(50);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS umbral_bajo NUMERIC(10,6);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS umbral_alto NUMERIC(10,6);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS origen_validacion VARCHAR(50);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS version_modelo VARCHAR(50);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS features_relevantes TEXT DEFAULT '[]';

UPDATE prescriptions
SET msi = CASE
    WHEN msi_alta IS TRUE THEN 'MSI-H'
    ELSE 'no_evaluado'
END
WHERE msi IS NULL;

UPDATE prescriptions
SET ras = CASE
    WHEN ras_mutado IS TRUE THEN 'mutado'
    ELSE 'no_evaluado'
END
WHERE ras IS NULL;

ALTER TABLE prescriptions ALTER COLUMN braf_v600e DROP DEFAULT;
ALTER TABLE prescriptions ALTER COLUMN braf_v600e TYPE VARCHAR(20) USING (
    CASE
        WHEN braf_v600e::text IN ('true', 't', '1') THEN 'presente'
        ELSE 'no_evaluado'
    END
);
ALTER TABLE prescriptions ALTER COLUMN braf_v600e SET DEFAULT 'no_evaluado';

UPDATE prescriptions SET msi = 'no_evaluado' WHERE msi IS NULL;
UPDATE prescriptions SET ras = 'no_evaluado' WHERE ras IS NULL;
UPDATE prescriptions SET braf_v600e = 'no_evaluado' WHERE braf_v600e IS NULL;
UPDATE prescriptions SET id_regimen = 'R00' WHERE id_regimen IS NULL;
UPDATE prescriptions SET dosis_por_farmaco = '[]' WHERE dosis_por_farmaco IS NULL;

ALTER TABLE prescriptions ALTER COLUMN msi SET DEFAULT 'no_evaluado';
ALTER TABLE prescriptions ALTER COLUMN ras SET DEFAULT 'no_evaluado';
ALTER TABLE prescriptions ALTER COLUMN msi SET NOT NULL;
ALTER TABLE prescriptions ALTER COLUMN ras SET NOT NULL;

ALTER TABLE prescriptions DROP COLUMN IF EXISTS msi_alta;
ALTER TABLE prescriptions DROP COLUMN IF EXISTS ras_mutado;
