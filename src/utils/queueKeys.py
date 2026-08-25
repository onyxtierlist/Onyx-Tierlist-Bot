def normalize_kit(kit: str) -> str:
    return str(kit).strip().lower()

def queue_key(kit: str) -> str:
    return normalize_kit(kit)
