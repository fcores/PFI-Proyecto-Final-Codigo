-- name: insert_user
INSERT INTO users (username, password_hash, salt, display_name, role)
VALUES (%s, %s, %s, %s, %s)
RETURNING id;

-- name: find_user_by_username
SELECT * FROM users WHERE username = %s AND active = TRUE;
