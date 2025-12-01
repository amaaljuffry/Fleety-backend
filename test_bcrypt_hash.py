#!/usr/bin/env python
import bcrypt

password = b'password123'
existing_hash = b'$2b$12$fMBgdSGUALrTFsrsgS80HOXVU2eYBiyy.SMUM3lVa5aYJr8tkA2qm'

# Generate a fresh hash
fresh_hash = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))
print(f"Fresh hash: {fresh_hash}")

# Try to verify with fresh hash
result_fresh = bcrypt.checkpw(password, fresh_hash)
print(f"Fresh hash verification: {result_fresh}")

# Try to verify with existing hash
result_existing = bcrypt.checkpw(password, existing_hash)
print(f"Existing hash verification: {result_existing}")

# Try different passwords with existing hash
for test_pwd in [b'password123', b'Password123', b'password', b'123456']:
    result = bcrypt.checkpw(test_pwd, existing_hash)
    print(f"  Testing '{test_pwd.decode()}': {result}")
