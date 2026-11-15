-- name: upgrade
DO $$
BEGIN
    IF to_regclass('public.users') IS NOT NULL THEN
        ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_role;
        ALTER TABLE users ADD CONSTRAINT chk_users_role
            CHECK (role IN ('administrador', 'prescriptor', 'auditor', 'financiador', 'super_admin'));
    END IF;
END $$;

-- name: downgrade
DO $$
BEGIN
    IF to_regclass('public.users') IS NOT NULL THEN
        UPDATE users SET active = FALSE WHERE role = 'financiador';
        ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_role;
        ALTER TABLE users ADD CONSTRAINT chk_users_role
            CHECK (role IN ('administrador', 'prescriptor', 'auditor', 'super_admin'))
            NOT VALID;
    END IF;
END $$;
