import hashlib, time, random

def make_id(*parts) -> str:
    raw = "|".join(map(str, parts)) + f"|{time.time()}|{random.random()}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]
