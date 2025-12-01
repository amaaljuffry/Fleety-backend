from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from app.config import settings


def hash_password(password: str) -> str:
    """
    Hash password using PBKDF2-SHA256 with a random salt.
    Format: sha256$iterations$salt$hash
    """
    salt = secrets.token_hex(32)  # 64 character hex string
    iterations = 100000
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode(),
        iterations
    )
    # Return formatted hash for compatibility
    return f"sha256${iterations}${salt}${pwd_hash.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against PBKDF2-SHA256 hash or bcrypt legacy hashes.
    Supports both new PBKDF2 format and legacy bcrypt format.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.debug(f"verify_password called with plain_password len={len(plain_password)}")
        logger.debug(f"hashed_password type={type(hashed_password)}, len={len(hashed_password) if hashed_password else 0}")
        
        if hashed_password is None:
            logger.error("hashed_password is None!")
            return False
            
        # Check for PBKDF2 format
        if hashed_password.startswith('sha256$'):
            logger.debug("Using PBKDF2 verification")
            parts = hashed_password.split('$')
            if len(parts) != 4:
                logger.error(f"PBKDF2 hash format invalid: {len(parts)} parts")
                return False
            _, iterations_str, salt, stored_hash = parts
            iterations = int(iterations_str)
            pwd_hash = hashlib.pbkdf2_hmac(
                'sha256',
                plain_password.encode('utf-8'),
                salt.encode(),
                iterations
            )
            result = pwd_hash.hex() == stored_hash
            logger.debug(f"PBKDF2 result: {result}")
            return result
        
        # Check for bcrypt format (legacy hashes from old system)
        elif hashed_password.startswith(('$2a$', '$2b$', '$2y$')):
            logger.debug(f"Using bcrypt verification, hash starts with: {hashed_password[:7]}")
            # Try to use bcrypt if available
            try:
                import bcrypt
                logger.debug(f"bcrypt version: {bcrypt.__version__}")
                result = bcrypt.checkpw(
                    plain_password.encode('utf-8'),
                    hashed_password.encode('utf-8')
                )
                logger.debug(f"bcrypt result: {result}")
                return result
            except Exception as e:
                logger.error(f"bcrypt check failed: {e}", exc_info=True)
                # If bcrypt check fails, return False
                return False
        else:
            logger.error(f"Hash format not recognized: {hashed_password[:20]}")
            return False
    except Exception as e:
        logger.error(f"verify_password exception: {e}", exc_info=True)
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None
