"""Login-session helpers used by every boundary (page) class."""
from functools import wraps
from flask import g, session, redirect, url_for, flash, abort
from app.entity.user_account import UserAccount


def load_logged_in_user():
    accountID = session.get("account_id")
    g.user = UserAccount.findById(accountID) if accountID else None
    if g.user is not None and not g.user.isActive():
        session.clear()
        g.user = None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login.displayLoginForm"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    """Only allow users whose profile is one of `roles`."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user.profileName not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator
