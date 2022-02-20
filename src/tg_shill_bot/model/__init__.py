from sqlalchemy.ext.declarative import declarative_base

from .chat_room import ChatRoom
from .chat_room_admin import ChatRoomAdmin
from .data_source import DataSource
from .link_tracker import LinkTracker
from .ads import Advertisement

Base = declarative_base()

__all__ = [
    "ChatRoom",
    "ChatRoomAdmin",
    "DataSource",
    "LinkTracker",
    "Advertisement",
]
