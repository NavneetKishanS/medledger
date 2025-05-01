from collections import defaultdict, deque

_MAX = 100
_ALERTS = defaultdict(lambda: deque(maxlen=_MAX))

def add_alert(username: str, record: dict) -> None:
    _ALERTS[username].appendleft(record)

def get_alerts(username: str) -> list[dict]:
    return list(_ALERTS[username])
