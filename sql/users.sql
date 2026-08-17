-- name: insert_user
INSERT INTO users (username, password_hash, salt, display_name, role)
VALUES (%s, %s, %s, %s, %s)
RETURNING id;

-- name: find_user_by_username
SELECT * FROM users WHERE username = %s AND active = TRUE;

-- name: find_user_any_by_username
SELECT * FROM users WHERE username = %s;

-- name: list_users
SELECT id, username, display_name, role, active, created_at
FROM users
ORDER BY id;

-- name: find_user_by_id
SELECT id, username, display_name, role, active, created_at
FROM users
WHERE id = %s;

-- name: update_user_profile
UPDATE users SET display_name = %s, role = %s, active = %s
WHERE id = %s
RETURNING id;

-- name: update_user_password
UPDATE users SET password_hash = %s, salt = %s
WHERE id = %s
RETURNING id;

-- name: update_user_password_by_username
UPDATE users SET password_hash = %s, salt = %s
WHERE username = %s;
