from abc import ABC, abstractmethod
from typing import Dict, Union

import base62

from app.internal.httpresponse import HTTPResponse


class AbstractURIParsingRepository(ABC):
    """ """

    @classmethod
    @abstractmethod
    def parse(cls, uri: str) -> Union[str, HTTPResponse]:
        pass


class Base62URIParsingRepository(ABC):
    @classmethod
    def parse(cls, uri: str) -> Union[str, HTTPResponse]:
        try:
            path = base62.decodebytes(uri).decode("utf-8")
            return path
        except Exception as e:
            return HTTPResponse(code=400, detail="given URI is not in base62")


SUPPORTED_FORMATS: Dict[str, AbstractURIParsingRepository] = {
    "BASE62": Base62URIParsingRepository
}
DEFAULT = Base62URIParsingRepository


def factory(kind: str) -> AbstractURIParsingRepository:
    return SUPPORTED_FORMATS.get(kind, DEFAULT)
