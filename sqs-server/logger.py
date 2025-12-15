import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("consumer_logs.jsonl")
Path("").mkdir(exist_ok=True)


def write_log(message: str):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": message,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def read_last_n_logs(n: int = 100):
    if not LOG_FILE.exists():
        return []

    with open(LOG_FILE, "r") as f:
        lines = f.readlines()

    last_lines = lines[-n:] if len(lines) > n else lines
    logs = []
    for line in last_lines:
        try:
            logs.append(json.loads(line.strip()))
        except json.JSONDecodeError:
            continue

    return logs


def clear_logs():
    if LOG_FILE.exists():
        LOG_FILE.unlink()
