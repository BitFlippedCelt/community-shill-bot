from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Table,
)
from sqlalchemy.orm import relationship

from tg_shill_bot.model.base import Base


# chat_room_data_source_table = Table('chat_rooms_data_sources', Base.metadata,
#     Column('chat_room_id', ForeignKey('chat_rooms.id'), primary_key=True),
#     Column('data_source_id', ForeignKey('data_sources.id'), primary_key=True)
# )


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    chat_room = relationship("ChatRoom", back_populates="data_sources")
    name = Column(String, nullable=False)
    ignore = Column(Boolean, nullable=False, default=False)
    data_source_type = Column(String, nullable=False, index=True)
