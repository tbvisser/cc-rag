import hashlib


def compute_content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
