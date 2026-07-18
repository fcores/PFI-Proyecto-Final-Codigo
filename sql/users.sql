-- name: insert_user
INSERT INTO users (username, password_hash, salt, display_name, role)
VALUES (%s, %s, %s, %s, %s)
RETURNING id;

-- name: find_user_by_username
SELECT * FROM users WHERE username = %s AND active = TRUE;

-- name: select_all_users
SELECT id, username, display_name, role, active, created_at FROM users ORDER BY id;
