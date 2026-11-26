mods = [
    "fastapi","starlette","sqlalchemy","alembic","aiosqlite","jinja2",
    "pydantic_settings","pytest","httpx","itsdangerous","markdown","bleach",
    "uvicorn","pydantic","greenlet","anyio"
]
for m in mods:
    try:
        mod = __import__(m)
        v = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
        print(f"{m}=={v}")
    except Exception as e:
        print(f"{m}=MISSING ({e})")
