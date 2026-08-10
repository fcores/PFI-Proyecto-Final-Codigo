CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    salt VARCHAR(64) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'prescriptor',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS monodrugs (
    id SERIAL PRIMARY KEY,
    descripcion VARCHAR(500) NOT NULL,
    codigo VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS medications (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL,
    descripcion VARCHAR(500) NOT NULL,
    ean VARCHAR(100) NOT NULL,
    codigo_alfabeta VARCHAR(100) NOT NULL,
    tipo_conservacion VARCHAR(200) NOT NULL,
    laboratorio VARCHAR(300) NOT NULL,
    monodroga VARCHAR(200) NOT NULL,
    tamano_dimension VARCHAR(200) NOT NULL,
    potencia_mg NUMERIC(12,4),
    unidad_potencia VARCHAR(50),
    precio NUMERIC(14,2),
    via_administracion VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patients (
    id SERIAL PRIMARY KEY,
    sap_id VARCHAR(100) NOT NULL,
    credential_id VARCHAR(100),
    provider_id VARCHAR(100),
    provider VARCHAR(200),
    first_name VARCHAR(200) NOT NULL,
    last_name VARCHAR(200) NOT NULL,
    birth_date DATE NOT NULL,
    gender VARCHAR(50) NOT NULL,
    treatment VARCHAR(500),
    medications TEXT DEFAULT '[]',
    hc_filename VARCHAR(500),
    ap_filename VARCHAR(500),
    img_filename VARCHAR(500),
    lab_filename VARCHAR(500),
    receta_filename VARCHAR(500),
    otros_filename VARCHAR(500),
    blockchain_tx_id VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prescriptions (
    id SERIAL PRIMARY KEY,
    prescription_code VARCHAR(50) NOT NULL,
    patient_sap_id VARCHAR(100) NOT NULL,
    edad INTEGER NOT NULL,
    sexo VARCHAR(50) NOT NULL,
    peso_kg NUMERIC(10,2) NOT NULL,
    talla_cm NUMERIC(10,2) NOT NULL,
    superficie_corporal_m2 NUMERIC(10,4) NOT NULL,
    diagnostico_cie10 VARCHAR(100) NOT NULL,
    localizacion_tumor VARCHAR(200) NOT NULL,
    tipo_histologico VARCHAR(200) NOT NULL,
    t VARCHAR(50) NOT NULL,
    n VARCHAR(50) NOT NULL,
    m VARCHAR(50) NOT NULL,
    estadio VARCHAR(50) NOT NULL,
    msi VARCHAR(20) NOT NULL DEFAULT 'no_evaluado',
    ras VARCHAR(20) NOT NULL DEFAULT 'no_evaluado',
    braf_v600e VARCHAR(20) NOT NULL DEFAULT 'no_evaluado',
    linea_tratamiento VARCHAR(100) NOT NULL,
    id_regimen VARCHAR(10) NOT NULL,
    esquema VARCHAR(500) NOT NULL,
    dosis_por_farmaco TEXT DEFAULT '[]',
    dosis_mg_m2 NUMERIC(10,2) NOT NULL,
    medico_prescriptor VARCHAR(200) NOT NULL,
    matricula VARCHAR(100) NOT NULL,
    estado_validacion VARCHAR(50) NOT NULL,
    motivos_validacion TEXT DEFAULT '[]',
    probabilidad_concordante NUMERIC(10,6),
    nivel_confianza VARCHAR(50),
    umbral_bajo NUMERIC(10,6),
    umbral_alto NUMERIC(10,6),
    origen_validacion VARCHAR(50),
    version_modelo VARCHAR(50),
    features_relevantes TEXT DEFAULT '[]',
    blockchain_tx_id VARCHAR(256),
    block_index INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ledger_blocks (
    index INTEGER PRIMARY KEY,
    timestamp VARCHAR(100) NOT NULL,
    tx_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    prev_hash VARCHAR(256) NOT NULL,
    hash VARCHAR(256) NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_cases (
    id SERIAL PRIMARY KEY,
    prescription_id INTEGER NOT NULL REFERENCES prescriptions(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pendiente',
    assigned_auditor VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dictamenes (
    id SERIAL PRIMARY KEY,
    audit_case_id INTEGER NOT NULL REFERENCES audit_cases(id),
    resultado VARCHAR(50) NOT NULL,
    justificacion TEXT NOT NULL,
    auditor_username VARCHAR(100) NOT NULL,
    blockchain_tx_id VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS corrections (
    id SERIAL PRIMARY KEY,
    audit_case_id INTEGER NOT NULL REFERENCES audit_cases(id),
    campo VARCHAR(200) NOT NULL,
    valor_anterior TEXT NOT NULL,
    valor_nuevo TEXT NOT NULL,
    justificacion TEXT NOT NULL,
    auditor_username VARCHAR(100) NOT NULL,
    blockchain_tx_id VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
