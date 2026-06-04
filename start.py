import os
import subprocess
import sys


COMMANDS = {
    "web": ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", os.environ.get("PORT", "8000")],
    "runner": [sys.executable, "-m", "app.agent.runner"],
    "outcome": [sys.executable, "-m", "app.agent.outcome"],
    "scoring": [sys.executable, "-m", "app.agent.scoring"],
    "f1-refresh": [sys.executable, "-m", "app.agent.f1_refresh"],
}


def main() -> int:
    process = os.environ.get("ATRIS_PROCESS", "web").strip().lower()
    command = COMMANDS.get(process)
    if command is None:
        valid = ", ".join(sorted(COMMANDS))
        raise SystemExit(f"Unknown ATRIS_PROCESS={process!r}. Expected one of: {valid}")

    os.chdir("backend")
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
