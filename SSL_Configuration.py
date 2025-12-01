import ssl
import certifi
import urllib.parse

def get_mongodb_uri_with_ssl():
    """
    Configure MongoDB URI with proper SSL/TLS settings for Windows
    """
    # Your current MongoDB URI
    original_uri = "mongodb+srv://username:password@cluster.mongodb.net/carlog?retryWrites=true&w=majority"
    
    # Add SSL parameters
    ssl_params = "&tlsAllowInvalidCertificates=false&tlsCAFile=" + urllib.parse.quote(certifi.where())
    
    return original_uri + ssl_params

def create_ssl_context():
    """
    Create a proper SSL context for Windows
    """
    context = ssl.create_default_context(cafile=certifi.where())
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context