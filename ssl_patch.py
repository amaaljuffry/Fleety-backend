"""
SSL/TLS Patch for Windows + Python 3.13 + MongoDB Atlas
This fixes the TLSV1_ALERT_INTERNAL_ERROR issue
"""
import ssl
import os

def patch_ssl_for_mongodb():
    """
    Patch SSL to work with MongoDB Atlas on Windows Python 3.13
    """
    try:
        # Set environment variable to allow legacy SSL
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        
        # Create a custom SSL context that allows old TLS versions
        original_create_default_context = ssl.create_default_context
        
        def create_custom_context(*args, **kwargs):
            context = original_create_default_context(*args, **kwargs)
            # Allow TLS 1.0 and 1.1 (normally disabled in Python 3.13)
            context.minimum_version = ssl.TLSVersion.TLSv1
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
        
        # Monkey patch SSL
        ssl.create_default_context = create_custom_context
        
        print("✅ SSL patch applied successfully")
        return True
        
    except Exception as e:
        print(f"⚠️ SSL patch failed: {e}")
        return False

# Apply patch when module is imported
patch_ssl_for_mongodb()
