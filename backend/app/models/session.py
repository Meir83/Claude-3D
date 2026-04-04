from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ChatSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    messages: Mapped[list["ChatMessage"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )
    jobs: Mapped[list["GenerationJob"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="session", cascade="all, delete-orphan", order_by="GenerationJob.created_at"
    )
