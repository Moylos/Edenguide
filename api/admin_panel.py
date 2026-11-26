from __future__ import annotations

import hmac
import logging
import os
import secrets

from flask import Flask, redirect, request, session, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.theme import Bootstrap4Theme
from flask_login import LoginManager, current_user, login_user, logout_user
from markupsafe import Markup
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session
from wtforms import PasswordField, StringField, TextAreaField
from wtforms.validators import DataRequired

logger = logging.getLogger(__name__)

from api.config import get_settings
from api.db import get_sync_session_factory
from api.models import Article, Character, Map, Role, Side, User
from api.security import verify_password


def _get_sync_session():
    SessionLocal = get_sync_session_factory()
    return SessionLocal()


class SecureAdminIndexView(AdminIndexView):
    @expose("/")
    def index(self):
        if not current_user.is_authenticated or getattr(current_user, "role", None) != "admin":
            return redirect(url_for(".login_view", next=request.url))
        return super().index()

    @staticmethod
    def _get_or_create_csrf_token() -> str:
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    @staticmethod
    def _validate_csrf_token(form_token: str | None) -> bool:
        session_token = session.get("_csrf_token")
        if not session_token or not form_token:
            return False
        return hmac.compare_digest(str(session_token), str(form_token))

    @expose("/login", methods=["GET", "POST"])
    def login_view(self):
        error = None
        if request.method == "POST":
            form_token = request.form.get("csrf_token")
            if not self._validate_csrf_token(form_token):
                session["_csrf_token"] = secrets.token_urlsafe(32)
                return self.render(
                    "admin/login.html",
                    error="Недействительный CSRF-токен. Обновите страницу и попробуйте снова.",
                    csrf_token=session["_csrf_token"],
                ), 400

            login = (request.form.get("login") or "").strip()
            password = request.form.get("password") or ""
            db = _get_sync_session()
            status_code = 200
            try:
                user = db.execute(select(User).where(User.login == login)).scalar_one_or_none()
                if (
                    user
                    and user.is_active
                    and user.role == "admin"
                    and verify_password(password, user.salt, user.pwd_hash)
                ):
                    db.expunge(user)
                    login_user(user)
                    session.pop("_csrf_token", None)
                    next_url = request.args.get("next") or url_for(".index")
                    return redirect(next_url)
                error = "Неверный логин или пароль."
            except (SQLAlchemyError, TimeoutError, OSError) as exc:
                logger.warning("Admin login DB query failed: %s", exc)
                error = "Сервис временно недоступен: база данных не отвечает. Попробуйте позже."
                status_code = 503
            finally:
                db.close()
            session["_csrf_token"] = secrets.token_urlsafe(32)
            csrf_token = session["_csrf_token"]
            return self.render("admin/login.html", error=error, csrf_token=csrf_token), status_code

        csrf_token = self._get_or_create_csrf_token()
        return self.render("admin/login.html", error=error, csrf_token=csrf_token)

    @expose("/logout")
    def logout_view(self):
        logout_user()
        return redirect(url_for(".login_view"))


class SecureModelView(ModelView):
    def is_accessible(self):
        return bool(current_user.is_authenticated and getattr(current_user, "role", None) == "admin")

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("admin.login_view", next=request.url))


class RoleAdmin(SecureModelView):
    column_list = ["id", "name", "description"]
    form_columns = ["name", "description"]
    column_searchable_list = ["name"]
    column_sortable_list = ["id", "name"]


class SideAdmin(SecureModelView):
    column_list = ["id", "name"]
    form_columns = ["name"]
    column_searchable_list = ["name"]
    column_sortable_list = ["id", "name"]


class MapAdmin(SecureModelView):
    column_list = ["id", "name", "description"]
    form_columns = ["name", "description"]
    column_searchable_list = ["name"]
    column_sortable_list = ["id", "name"]


class CharacterAdmin(SecureModelView):
    column_list = ["id", "name", "role", "icon_url"]
    form_columns = ["name", "role", "description", "icon_url"]
    column_searchable_list = ["name"]
    column_sortable_list = ["id", "name"]
    column_filters = ["role.name"]


class ArticleAdmin(SecureModelView):
    column_list = ["id", "title", "map", "side", "role", "created_at"]
    form_columns = ["title", "content", "map", "side", "role", "characters"]
    column_searchable_list = ["title"]
    column_sortable_list = ["id", "title", "created_at"]
    column_filters = ["map.name", "side.name", "role.name"]
    form_overrides = {"content": TextAreaField}
    form_widget_args = {
        "content": {
            "rows": 20,
            "placeholder": "Markdown supported. Use #, *, lists, code blocks, etc.",
        }
    }
    form_args = {
        "content": {
            "label": "Content (Markdown)",
            "description": "Поддерживается Markdown-разметка.",
        }
    }
    column_formatters = {
        "content": lambda v, c, m, p: Markup("<em>Markdown</em>") if m.content else "",
    }


class UserAdmin(SecureModelView):
    column_list = ["id", "login", "role", "is_active", "subscription_status", "created_at"]
    column_searchable_list = ["login"]
    column_sortable_list = ["id", "login", "role", "created_at"]
    column_filters = ["role", "is_active"]
    form_columns = ["login", "email", "role", "is_active", "subscription_status", "subscription_until"]
    can_create = False
    can_delete = False


def create_admin_app() -> Flask:
    settings = get_settings()
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_dir = os.path.join(base_dir, "ui", "admin_templates")

    flask_app = Flask(
        __name__,
        template_folder=template_dir,
    )
    flask_app.config["SECRET_KEY"] = settings.secret_key
    flask_app.config["SESSION_COOKIE_NAME"] = "edenguide_admin_session"
    flask_app.config["SESSION_COOKIE_HTTPONLY"] = True
    flask_app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    flask_app.config["SESSION_COOKIE_SECURE"] = settings.is_production

    login_manager = LoginManager()
    login_manager.init_app(flask_app)
    login_manager.login_view = "admin.login_view"

    @login_manager.user_loader
    def load_user(user_id: str):
        db = _get_sync_session()
        try:
            try:
                uid = int(user_id)
            except (TypeError, ValueError):
                return None
            user = db.get(User, uid)
            if user is not None:
                db.expunge(user)
            return user
        finally:
            db.close()

    SessionLocal = get_sync_session_factory()
    db_session = scoped_session(SessionLocal)

    @flask_app.teardown_appcontext
    def remove_session(exception=None):
        db_session.remove()

    admin = Admin(
        flask_app,
        name="Edenguide Admin",
        url="/",
        index_view=SecureAdminIndexView(name="Dashboard", url="/"),
        theme=Bootstrap4Theme(),
    )

    admin.add_view(RoleAdmin(Role, db_session, name="Roles", category="VALORANT"))
    admin.add_view(SideAdmin(Side, db_session, name="Sides", category="VALORANT"))
    admin.add_view(MapAdmin(Map, db_session, name="Maps", category="VALORANT"))
    admin.add_view(CharacterAdmin(Character, db_session, name="Characters", category="VALORANT"))
    admin.add_view(ArticleAdmin(Article, db_session, name="Articles", category="VALORANT"))
    admin.add_view(UserAdmin(User, db_session, name="Users", category="System"))

    return flask_app
