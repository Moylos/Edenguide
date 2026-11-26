import importlib.metadata as m
for p in ['pytest-asyncio','python-dotenv','anyio']:
    try:
        print(p, m.version(p))
    except Exception as e:
        print(p, 'MISSING')
