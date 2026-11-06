"""Create the bcrypt hash for the admin passcode.

    python -m app.hash_passcode "my passcode"           # print the hash
    python -m app.hash_passcode "my passcode" --write   # also save it to ../.env
"""
import sys

from .config import PROJECT_ROOT
from .security import hash_passcode


def write_env(hashed: str) -> None:
    env = PROJECT_ROOT / ".env"
    example = PROJECT_ROOT / ".env.example"
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else (
        example.read_text(encoding="utf-8").splitlines() if example.exists() else []
    )
    lines = [ln for ln in lines if not ln.startswith("ADMIN_PASSCODE_HASH=")]
    lines.append(f"ADMIN_PASSCODE_HASH={hashed}")
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved ADMIN_PASSCODE_HASH to {env}")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args or len(args[0]) < 6:
        print("Usage: python -m app.hash_passcode <passcode (6+ characters)> [--write]")
        return 1
    hashed = hash_passcode(args[0])
    if "--write" in sys.argv:
        write_env(hashed)
    else:
        print(hashed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
