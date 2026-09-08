import hashlib,hmac
def verify_signature(raw_body,signature,secret):
    if not signature or not secret: return False
    return hmac.compare_digest(hmac.new(secret.encode(),raw_body,hashlib.sha256).hexdigest(),signature)
