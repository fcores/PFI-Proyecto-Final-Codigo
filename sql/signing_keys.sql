-- name: find_active_key
SELECT id, username, algoritmo, public_key_pem, private_key_enc, key_fingerprint, created_at, revoked_at
FROM user_signing_keys
WHERE username = %s AND revoked_at IS NULL
ORDER BY created_at DESC
LIMIT 1;

-- name: find_key_by_fingerprint
SELECT id, username, algoritmo, public_key_pem, private_key_enc, key_fingerprint, created_at, revoked_at
FROM user_signing_keys
WHERE key_fingerprint = %s;

-- name: insert_key
INSERT INTO user_signing_keys (username, algoritmo, public_key_pem, private_key_enc, key_fingerprint)
VALUES (%s, %s, %s, %s, %s)
RETURNING id;

-- name: revoke_keys
UPDATE user_signing_keys SET revoked_at = NOW()
WHERE username = %s AND revoked_at IS NULL;
