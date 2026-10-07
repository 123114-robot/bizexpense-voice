from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models import (  # noqa: E402,F401
    category,
    document,
    expense,
    refresh_token,
    supplier,
    user,
)
