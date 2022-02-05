from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ShillLinkTracker(Base):
    __tablename__ = "shill_link_tracker"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, index=True)
    link = Column(String, nullable=False)
    link_type = Column(String, nullable=False, index=True)
    checked = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
