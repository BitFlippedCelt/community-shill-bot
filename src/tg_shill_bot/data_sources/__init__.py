import abc
import re
import typing


class SocialDataSource(metaclass=abc.ABCMeta):
    link_pattern = re.compile(r"(.*)")

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "find_links")
            and hasattr(subclass, "get_recent")
            and hasattr(subclass, "check_engagement")
            and callable(subclass.find_links)
            and callable(subclass.get_recent)
            and callable(subclass.check_engagement)
            or NotImplemented
        )

    @classmethod
    def find_links(cls, message: str) -> typing.List[typing.Match[str]]:
        links = []
        for match in cls.link_pattern.finditer(message):
            links.append(match)

        return links

    @abc.abstractmethod
    def get_recent(self, **kwargs):
        """Load recent data from the data source"""
        raise NotImplementedError

    @abc.abstractmethod
    def check_engagement(self, **kwargs):
        """Check engagement with the data source"""
        raise NotImplementedError
