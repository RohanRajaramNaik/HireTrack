"""Reset a user's password from the command line (for a locked-out administrator).

    cd backend
    python -m app.reset_password admin@hiretrack.local "NewPassw0rd"

The account is also re-activated. The new password must follow the same rule
as the app: at least 8 characters with a letter and a number.
"""
from __future__ import annotations

import sys

from sqlalchemy import select

from .database import SessionLocal, init_db
from .models import User
from .schemas import PASSWORD_RULE, _check_password
from .security import hash_password


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    email, password = argv[0].strip().lower(), argv[1]
    try:
        _check_password(password)
    except ValueError:
        print(PASSWORD_RULE)
        return 1
    init_db()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"No user with email {email}")
            return 1
        user.password_hash = hash_password(password)
        user.is_active = True
        db.commit()
    print(f"Password reset for {email}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
