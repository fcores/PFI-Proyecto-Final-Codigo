-- name: insert_token
INSERT INTO auth_tokens (token_hash, username, display_name, role, expires_at)
VALUES (%s, %s, %s, %s, NOW() + make_interval(hours => %s));

-- name: find_valid_token
-- El rol y el estado se leen de users (no de la fila del token): un cambio de
-- rol o una baja surten efecto en la proxima resolucion de la sesion.
SELECT u.username, u.display_name, u.role
FROM auth_tokens t
JOIN users u ON u.username = t.username
WHERE t.token_hash = %s AND t.expires_at > NOW() AND u.active = TRUE;

-- name: delete_token
DELETE FROM auth_tokens WHERE token_hash = %s;

-- name: delete_tokens_by_username
DELETE FROM auth_tokens WHERE username = %s;

-- name: delete_other_tokens_by_username
DELETE FROM auth_tokens WHERE username = %s AND token_hash <> %s;

-- name: purge_expired_tokens
DELETE FROM auth_tokens WHERE expires_at <= NOW();
