import hashlib
import os
import sqlite3


def pwd_hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000).hex()


con = sqlite3.connect("data/app.db")
con.execute("DROP TABLE IF EXISTS users")
con.execute(
    "CREATE TABLE users(id INTEGER PRIMARY KEY, login TEXT UNIQUE NOT NULL, "
    "salt TEXT NOT NULL, pwd_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user')"
)
for login, password, role in [
    ("admin", "admin123", "admin"),
    ("student", "student123", "user"),
    ("guest", "guest123", "user"),
]:
    salt = os.urandom(16)
    con.execute(
        "INSERT INTO users(login, salt, pwd_hash, role) VALUES (?, ?, ?, ?)",
        (login, salt.hex(), pwd_hash(password, salt), role),
    )
con.commit()
print(con.execute("SELECT login, role FROM users").fetchall())
con.close()
