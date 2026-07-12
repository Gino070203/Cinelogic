from sqlalchemy import Column, Integer, DateTime, UniqueConstraint, ForeignKey
from datetime import datetime, timezone
from database import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_user_movie"),
    )
