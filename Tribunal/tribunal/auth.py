"""Authentication helpers for the Tribunal app."""

from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar

from flask import flash, redirect, session, url_for


F = TypeVar("F", bound=Callable[..., object])


def login_required(view: F) -> F:
    """Minimal session-based access control decorator."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesi?n para acceder a esta p?gina.", "error")
            return redirect(url_for("web.login"))
        return view(*args, **kwargs)

    return wrapped  # type: ignore[return-value]
