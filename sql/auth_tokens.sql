-- name: insert_token
INSERT INTO auth_tokens (token_hash, username, display_name, role, expires_at)
VALUES (%s, %s, %s, %s, NOW() + make_interval(hours => %s));

-- name: find_valid_token
SELECT username, display_name, role
FROM auth_tokens
WHERE token_hash = %s AND expires_at > NOW();

-- name: delete_token
DELETE FROM auth_tokens WHERE token_hash = %s;

-- name: purge_expired_tokens
DELETE FROM auth_tokens WHERE expires_at <= NOW();
