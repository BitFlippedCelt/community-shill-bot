from datetime import datetime

from sqlalchemy import BLOB, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ShillChatRoomSettings(Base):
    __tablename__ = "shill_chat_room_settings"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, nullable=False, index=True)
    name = Column(String, nullable=False)
    token = Column(String)
    cta_link = Column(String)
    cta_text = Column(String)
    dex_link = Column(String)
    cmc_link = Column(String)
    cg_link = Column(String)
    tags = Column(String)
    logo = Column(String)
    scrape_interval = Column(Integer, nullable=False, default=60 * 60)
    update_interval = Column(Integer, nullable=False, default=60 * 30)
