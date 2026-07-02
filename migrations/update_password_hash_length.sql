-- Migration to update password_hash and secret_answer_hash field lengths
-- This fixes the StringDataRightTruncation error for scrypt hashes

-- Update user table
ALTER TABLE "user" ALTER COLUMN password_hash TYPE VARCHAR(255);
ALTER TABLE "user" ALTER COLUMN secret_answer_hash TYPE VARCHAR(255);

-- Update password_history table
ALTER TABLE password_history ALTER COLUMN password_hash TYPE VARCHAR(255);

-- Verify the changes
SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'user' AND column_name IN ('password_hash', 'secret_answer_hash');

SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'password_history' AND column_name = 'password_hash';






