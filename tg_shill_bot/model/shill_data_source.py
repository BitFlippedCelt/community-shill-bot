from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ShillDataSource(Base):
    __tablename__ = "shill_data_sources"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, index=True)
    name = Column(String, nullable=False)
    ignore = Column(Boolean, nullable=False, default=False)
    data_source_type = Column(String, nullable=False, index=True)
