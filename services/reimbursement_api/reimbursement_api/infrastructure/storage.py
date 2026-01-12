from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    def save(self, file, filename):
        pass

    @abstractmethod
    def retrieve(self, filename):
        pass
