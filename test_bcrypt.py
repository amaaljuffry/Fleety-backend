#!/usr/bin/env python
import bcrypt

password = b'password123'
hash_from_db = b'$2b$12$fMBgdSGUALrTFsrsgS80HOXVU2eYBiyy.SMUM3lVa5aYJr8tkA2qm'

print(f"Password: {password}")
print(f"Hash: {hash_from_db}")
print(f"Hash length: {len(hash_from_db)}")

try:
    result = bcrypt.checkpw(password, hash_from_db)
    print(f"Bcrypt result: {result}")
except Exception as e:
    print(f"Bcrypt error: {e}")
