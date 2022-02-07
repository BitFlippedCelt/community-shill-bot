import abc
import typing


class SocialDataSource(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "get_recent")
            and callable(subclass.get_recent)
            or NotImplemented
        )

    @abc.abstractmethod
    def get_recent(self, **kwargs):
        """Load recent data from the data source"""
        raise NotImplementedError

    @abc.abstractmethod
    def check_engagement(self, **kwargs):
        """Check engagement with the data source"""
        raise NotImplementedError
