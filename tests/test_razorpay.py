import hashlib,hmac
from app.services.razorpay import verify_signature

def test_razorpay_signature_validation():
    body=b'{"event":"payment.captured"}'; secret="webhook-secret"
    signature=hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()
    assert verify_signature(body,signature,secret)
    assert not verify_signature(body,"bad",secret)
