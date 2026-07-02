-- Migration: Add 2FA columns to User table
-- Description: Adds two-factor authentication support to the User table
-- Database: PostgreSQL (Neon)
-- Date: 2025-08-08
-- Author: AFROTC 695 Recruitment System

-- Add 2FA columns to User table
-- Note: All columns are nullable to ensure backward compatibility with existing data

-- TOTP secret key (encrypted in application layer)
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(255);

-- Flag to indicate if 2FA is enabled for this user
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE;

-- Encrypted backup codes for account recovery
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS backup_codes_hash TEXT;

-- Flag to track if 2FA setup has been completed
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS totp_setup_completed BOOLEAN DEFAULT FALSE;

-- Admin control flag to allow/disallow 2FA for specific users
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS can_enable_2fa BOOLEAN DEFAULT TRUE;

-- Create index for performance on 2FA-enabled users
CREATE INDEX IF NOT EXISTS idx_user_totp_enabled ON "user"(totp_enabled);

-- Create index for performance on users who can enable 2FA
CREATE INDEX IF NOT EXISTS idx_user_can_enable_2fa ON "user"(can_enable_2fa);

-- Add comments for documentation
COMMENT ON COLUMN "user".totp_secret IS 'Encrypted TOTP secret key for 2FA authentication';
COMMENT ON COLUMN "user".totp_enabled IS 'Whether 2FA is enabled for this user';
COMMENT ON COLUMN "user".backup_codes_hash IS 'Encrypted backup codes for account recovery';
COMMENT ON COLUMN "user".totp_setup_completed IS 'Whether 2FA setup has been completed';
COMMENT ON COLUMN "user".can_enable_2fa IS 'Admin control flag to allow/disallow 2FA for this user';

-- Verify the migration
DO $$
BEGIN
    -- Check if columns were added successfully
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user' 
        AND column_name = 'totp_secret'
    ) THEN
        RAISE EXCEPTION 'Migration failed: totp_secret column not found';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user' 
        AND column_name = 'totp_enabled'
    ) THEN
        RAISE EXCEPTION 'Migration failed: totp_enabled column not found';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user' 
        AND column_name = 'backup_codes_hash'
    ) THEN
        RAISE EXCEPTION 'Migration failed: backup_codes_hash column not found';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user' 
        AND column_name = 'totp_setup_completed'
    ) THEN
        RAISE EXCEPTION 'Migration failed: totp_setup_completed column not found';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user' 
        AND column_name = 'can_enable_2fa'
    ) THEN
        RAISE EXCEPTION 'Migration failed: can_enable_2fa column not found';
    END IF;
    
    RAISE NOTICE 'Migration completed successfully: All 2FA columns added to User table';
END $$;

-- Rollback script (for reference - uncomment to rollback)
/*
-- Remove indexes
DROP INDEX IF EXISTS idx_user_totp_enabled;
DROP INDEX IF EXISTS idx_user_can_enable_2fa;

-- Remove columns
ALTER TABLE "user" DROP COLUMN IF EXISTS totp_secret;
ALTER TABLE "user" DROP COLUMN IF EXISTS totp_enabled;
ALTER TABLE "user" DROP COLUMN IF EXISTS backup_codes_hash;
ALTER TABLE "user" DROP COLUMN IF EXISTS totp_setup_completed;
ALTER TABLE "user" DROP COLUMN IF EXISTS can_enable_2fa;
*/
