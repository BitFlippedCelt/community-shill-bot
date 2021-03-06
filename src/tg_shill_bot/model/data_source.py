from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from tg_shill_bot.model.base import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    chat_room = relationship("ChatRoom", back_populates="data_sources")
    name = Column(String, nullable=False)
    ignore = Column(Boolean, nullable=False, default=False)
    data_source_type = Column(String, nullable=False, index=True)
