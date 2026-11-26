# Edenguide

Веб-платформа Edenguide по VALORANT: публичные страницы, библиотека материалов, тирлист агентов, авторизация и админ-панель.

## Стек

- **Backend:** Python 3.13, FastAPI, SQLAlchemy (async), Alembic
- **БД:** SQLite для локальной разработки (по умолчанию в `.env`), PostgreSQL — целевая БД для продакшена/дальнейшего развёртывания
- **Frontend:** Jinja2 templates, vanilla JS, CSS
- **Админка:** Flask-Admin, смонтированная в FastAPI через `a2wsgi`
- **Тесты:** pytest, httpx ASGITransport

## Структура проекта

```text
opencode_project/
  api/                  # FastAPI-приложение, роутеры, модели, зависимости, безопасность
    routers/            # public/auth/admin/tierlist API и страницы
  alembic/              # Миграции БД
  data/                 # Локальная SQLite-БД и runtime-данные (не коммитятся)
  scripts/              # Служебные скрипты (seed, init_db и др.)
  tests/                # pytest-тесты
  ui/                   # Шаблоны и статика
    templates/          # Jinja2 HTML
    static/             # CSS/JS/изображения
  .env.example          # Пример переменных окружения
  requirements.txt      # Зависимости Python
```

## Локальный запуск (SQLite)

Команды выполняются из каталога `python-3.13.12-embed-amd64\opencode_project`.

1. Подготовьте окружение и зависимости:

```bat
cmd /c env.cmd
..\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

2. В `.env` для локального запуска используйте SQLite:

```env
APP_ENV=development
SECRET_KEY=change-me-in-production
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_CHAT_ID=
```

3. Примените миграции:

```bat
cmd /c env.cmd
..\python.exe -m alembic upgrade head
```

4. (Опционально) заполните dev-данными:

```bat
cmd /c env.cmd
..\python.exe scripts\seed.py
```

Seed создаёт демо-пользователей **только для локальной разработки**:

| Логин | Пароль | Роль |
|---|---|---|
| `admin` | `admin123` | admin |
| `student` | `student123` | user |
| `guest` | `guest123` | user |

> Перед любым публичным/продакшен-развёртыванием смените `SECRET_KEY`, не используйте демо-пароли и настройте реальную БД/секреты через переменные окружения.

5. Запустите приложение:

```bat
cmd /c env.cmd
..\python.exe -m uvicorn api.main:app --reload
```

Проверка: `http://127.0.0.1:8000/api/health` должен вернуть `{"status":"ok"}`.

## Переменные окружения

| Переменная | Назначение | Пример/значение по умолчанию |
|---|---|---|
| `APP_ENV` | Режим приложения (`development`/`production`) | `development` |
| `SECRET_KEY` | Секрет для сессий/CSRF | заменить на случайное значение |
| `DATABASE_URL` | Async SQLAlchemy URL БД | SQLite: `sqlite+aiosqlite:///./data/app.db`; Postgres: `postgresql+asyncpg://user:pass@host:5432/db` |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота для уведомлений | пусто локально |
| `TELEGRAM_ADMIN_CHAT_ID` | Chat ID для админ-уведомлений | пусто локально |

Реальные секреты храните только в `.env`/секретах окружения. В репозитории должен быть только `.env.example`.

## Миграции

```bat
cmd /c env.cmd
..\python.exe -m alembic upgrade head
```

Создание новой миграции (при изменении моделей):

```bat
cmd /c env.cmd
..\python.exe -m alembic revision --autogenerate -m "describe_change"
```

## Тесты

```bat
cmd /c env.cmd
..\python.exe -m pytest -q
```

## Админка

- Обычная админ-панель: `/admin-panel` (требует роль `admin`).
- Flask-Admin: `/admin`.
- Тирлист: `/tierlist`; администратор может перетаскивать агентов и сохранять расстановку. Сохранение выполняется через `PUT /api/tierlist` и хранится в таблице `tierlist_state` в БД, поэтому сохраняется после перезагрузки страницы и перезапуска сервера.

## Переход на PostgreSQL

PostgreSQL — целевая БД. Для локальной проверки установите драйверы из `requirements.txt`, поднимите PostgreSQL и укажите:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/edenguide
```

Затем примените миграции `alembic upgrade head`. Перед публикацией/деплоем не используйте дефолтные учётные данные.
