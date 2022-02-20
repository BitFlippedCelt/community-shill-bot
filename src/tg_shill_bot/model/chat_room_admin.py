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


class ChatRoomAdmin(Base):
    __tablename__ = "chat_room_admins"

    id = Column(Integer, primary_key=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    chat_room = relationship("ChatRoom", back_populates="chat_room_admins")
    user_id = Column(BigInteger, nullable=False)
