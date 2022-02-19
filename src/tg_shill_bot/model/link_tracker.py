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


# chat_room_link_table = Table('chat_rooms_link_trackers', Base.metadata,
#     Column('chat_room_id', ForeignKey('chat_rooms.id'), primary_key=True),
#     Column('link_tracker_id', ForeignKey('link_trackers.id'), primary_key=True)
# )


class LinkTracker(Base):
    __tablename__ = "link_trackers"

    id = Column(Integer, primary_key=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    chat_room = relationship("ChatRoom", back_populates="link_trackers")
    link = Column(String, nullable=False)
    link_type = Column(String, nullable=False, index=True)
    checked = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
