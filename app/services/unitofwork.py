from abc import ABC, abstractmethod
from os import chdir, curdir
from typing import Dict, Union
from pathlib import Path

from app.models.program import Program
from app.adapters.newaverepository import (
    AbstractNewaveRepository,
    RawNewaveRepository,
)
from app.adapters.decomprepository import (
    AbstractDecompRepository,
    RawDecompRepository,
)


class AbstractUnitOfWork(ABC):
    def __enter__(self) -> "AbstractUnitOfWork":
        return self

    def __exit__(self, *args):
        self.rollback()

    @abstractmethod
    def rollback(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def program(self) -> Program:
        raise NotImplementedError

    @property
    @abstractmethod
    def files(
        self,
    ) -> Union[AbstractNewaveRepository, AbstractDecompRepository]:
        raise NotImplementedError


class NewaveUnitOfWork(AbstractUnitOfWork):
    def __init__(self, directory: str):
        self._current_path = Path(curdir).resolve()
        self._case_directory = directory
        self._newave = None

    def __create_repository(self):
        if self._newave is None:
            self._newave = RawNewaveRepository(str(self._case_directory))

    def __enter__(self) -> "NewaveUnitOfWork":
        chdir(self._case_directory)
        self.__create_repository()
        return super().__enter__()

    def __exit__(self, *args):
        chdir(self._current_path)
        super().__exit__(*args)

    @property
    def program(self) -> Program:
        return Program.NEWAVE

    @property
    def files(self) -> AbstractNewaveRepository:
        return self._newave

    def rollback(self):
        pass


class DecompUnitOfWork(AbstractUnitOfWork):
    def __init__(self, directory: str):
        self._current_path = Path(curdir).resolve()
        self._case_directory = directory
        self._decomp = None

    def __create_repository(self):
        if self._decomp is None:
            self._decomp = RawDecompRepository(str(self._case_directory))

    def __enter__(self) -> "DecompUnitOfWork":
        chdir(self._case_directory)
        self.__create_repository()
        return super().__enter__()

    def __exit__(self, *args):
        chdir(self._current_path)
        super().__exit__(*args)

    @property
    def program(self) -> Program:
        return Program.DECOMP

    @property
    def files(self) -> AbstractDecompRepository:
        return self._decomp

    def rollback(self):
        pass


def factory(kind: Program, *args, **kwargs) -> AbstractUnitOfWork:
    mappings: Dict[Program, AbstractUnitOfWork] = {
        Program.NEWAVE: NewaveUnitOfWork,
        Program.DECOMP: DecompUnitOfWork,
    }
    return mappings[kind](*args, **kwargs)
