from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REQUIRED_ENV = [
    "DATABASE_URL",
    "BOOTSTRAP",
    "ANTHROPIC_API_KEY",
    "EMBEDDING_MODEL",
    "KB_TOP_K",
]


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _check_docker() -> bool:
    try:
        subprocess.run(
            ["docker", "info"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    env_path = repo_root / ".env"
    env_data = _read_env_file(env_path)

    print("== Environment ==")
    if not env_path.exists():
        print("Missing .env (copy from .env.example)")
    else:
        missing = [k for k in REQUIRED_ENV if not env_data.get(k)]
        if missing:
            print(f"Missing env vars: {', '.join(missing)}")
        else:
            print("Env looks good")

    print("== Tooling ==")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Docker running: {'yes' if _check_docker() else 'no'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
