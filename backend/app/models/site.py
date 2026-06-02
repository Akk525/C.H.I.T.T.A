from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # PostGIS-ready; requires `CREATE EXTENSION postgis;`
    geom: Mapped[str] = mapped_column(Geometry("POINT", srid=4326), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

