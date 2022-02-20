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


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True)
    chat_type = Column(SmallInteger, nullable=False, default=0)
    chat_id = Column(BigInteger, nullable=False, index=True)

    name = Column(String, nullable=False)
    token = Column(String)

    cta_link = Column(String)
    cta_text = Column(String)
    dex_link = Column(String)
    cmc_link = Column(String)
    cg_link = Column(String)

    tags = Column(String)
    logo_url = Column(String)

    link_count = Column(Integer, nullable=False, default=20)
    link_age = Column(Integer, nullable=False, default=60)
    scrape_count = Column(Integer, nullable=False, default=20)

    scrape_interval = Column(Integer, nullable=False, default=60 * 60)
    update_interval = Column(Integer, nullable=False, default=60 * 30)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    chat_room_admins = relationship("ChatRoomAdmin")
    data_sources = relationship("DataSource")
    link_trackers = relationship("LinkTracker")
