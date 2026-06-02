from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SiteAnalysis(Base):
    __tablename__ = "site_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False)

    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    report: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

