from datetime import datetime

from sqlalchemy import (
    BLOB,
    BigInteger,
    Column,
    Integer,
    SmallInteger,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Table,
)
from sqlalchemy.orm import relationship

from tg_shill_bot.model.base import Base


class Advertisement(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)
    token = Column(String)

    link = Column(String, nullable=False)
    chart_link = Column(String)
    buy_link = Column(String)
    priority = Column(Integer, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
