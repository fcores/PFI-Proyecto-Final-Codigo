-- name: insert_block
INSERT INTO ledger_blocks (index, timestamp, tx_type, payload, prev_hash, hash)
VALUES (%s, %s, %s, %s, %s, %s);

-- name: select_all_blocks
SELECT * FROM ledger_blocks ORDER BY index;

-- name: select_last_block
SELECT * FROM ledger_blocks ORDER BY index DESC LIMIT 1;

-- name: count_blocks
SELECT COUNT(*) FROM ledger_blocks;
