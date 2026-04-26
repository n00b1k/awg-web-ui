import os
import subprocess

def generate_self_signed_cert(cert_file, key_file):
    """Генерация самоподписанного сертификата"""
    from config import CERT_DIR
    print("Generating self-signed certificate...")
    
    os.makedirs(CERT_DIR, exist_ok=True)
    
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:4096",
        "-nodes", "-out", cert_file, "-keyout", key_file,
        "-days", "365", "-subj", "/CN=localhost"
    ], check=True, capture_output=True)
    
    os.chmod(key_file, 0o600)
    os.chmod(cert_file, 0o644)
    
    print(f"Self-signed certificate saved to {cert_file}")
    return cert_file, key_file

def get_ssl_context(cert_file, key_file):
    """Получение SSL контекста"""
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"Using SSL certificate from: {cert_file}")
        print(f"Using SSL key from: {key_file}")
        return (cert_file, key_file)
    
    return generate_self_signed_cert(cert_file, key_file)

def print_config_info():
    from config import AUTO_START_SERVERS, FLASK_PORT
    print("=" * 50)
    print(f"AmneziaWG Web UI starting on port {FLASK_PORT}")
    print(f"Auto-start servers: {AUTO_START_SERVERS}")
    print("=" * 50)