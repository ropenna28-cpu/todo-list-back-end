from datetime import datetime, timezone

def agora_utc() -> datetime:
    """Devolve a data e hora atual em UTC, com timezone definido."""
    return datetime.now(timezone.utc)
