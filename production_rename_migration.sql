-- Migration Script for Existing Production Users
-- Run this on your production database to migrate the 5 existing users over to Kaelen Financial

BEGIN;

-- 1. Update the hardcoded Bank Name
UPDATE accounts 
SET bank_name = 'Kaelen Financial' 
WHERE bank_name = 'Arcteron Trust';

-- 2. Update the SWIFT code prefix (replaces ARCT with KFIN while preserving the currency part)
UPDATE accounts 
SET swift_code = REPLACE(swift_code, 'ARCT', 'KFIN') 
WHERE swift_code LIKE 'ARCT%';

-- 3. Update the admin and support emails in the users table
UPDATE users
SET email = REPLACE(email, '@arcterontrust.com', '@kaelenfinancial.com')
WHERE email LIKE '%@arcterontrust.com';

-- Review updates before committing:
-- SELECT id, account_number, bank_name, swift_code FROM accounts LIMIT 5;
-- SELECT id, email FROM users WHERE email LIKE '%@kaelenfinancial.com';

COMMIT;
