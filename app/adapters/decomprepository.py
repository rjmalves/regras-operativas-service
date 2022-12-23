from abc import ABC, abstractmethod
from typing import Dict, Type, Optional, Union
import pathlib

from idecomp.decomp.caso import Caso
from idecomp.decomp.arquivos import Arquivos
from idecomp.decomp.dadger import Dadger
from idecomp.decomp.dadgnl import DadGNL
from idecomp.decomp.inviabunic import InviabUnic
from idecomp.decomp.relato import Relato
from idecomp.decomp.relgnl import RelGNL
from idecomp.decomp.hidr import Hidr

from app.internal.settings import Settings
from app.utils.encoding import converte_codificacao
from app.utils.log import Log
from app.internal.httpresponse import HTTPResponse


class AbstractDecompRepository(ABC):
    @property
    @abstractmethod
    def caso(self) -> Union[Caso, HTTPResponse]:
        raise NotImplementedError

    @property
    @abstractmethod
    def arquivos(self) -> Union[Arquivos, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    async def get_dadger(self) -> Union[Dadger, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_dadger(self, d: Dadger) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    async def get_dadgnl(self) -> Union[DadGNL, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_dadgnl(self, d: DadGNL) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    def get_inviabunic(self) -> Union[InviabUnic, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def get_relato(self) -> Union[Relato, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def get_relgnl(self) -> Union[RelGNL, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def get_hidr(self) -> Union[Hidr, HTTPResponse]:
        raise NotImplementedError


class RawDecompRepository(AbstractDecompRepository):
    def __init__(self, path: str):
        self.__path = path
        try:
            self.__caso = Caso.le_arquivo(str(self.__path))
        except FileNotFoundError:
            Log.log().error("Não foi encontrado o arquivo caso.dat")
        self.__arquivos: Optional[Arquivos] = None
        self.__dadger: Optional[Dadger] = None
        self.__read_dadger = False
        self.__dadgnl: Optional[DadGNL] = None
        self.__read_dadgnl = False
        self.__relato: Optional[Relato] = None
        self.__read_relato = False
        self.__relgnl: Optional[RelGNL] = None
        self.__read_relgnl = False
        self.__inviabunic: Optional[InviabUnic] = None
        self.__read_inviabunic = False
        self.__hidr: Optional[Hidr] = None
        self.__read_hidr = False

    @property
    def caso(self) -> Caso:
        return self.__caso

    @property
    def arquivos(self) -> Union[Arquivos, HTTPResponse]:
        if self.__arquivos is None:
            try:
                self.__arquivos = Arquivos.le_arquivo(
                    self.__path, self.__caso.arquivos
                )
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.__caso.arquivos}"
                Log.log().error(msg)
                return HTTPResponse(code=404, detail=msg)
        return self.__arquivos

    async def get_dadger(self) -> Union[Dadger, HTTPResponse]:
        if self.__read_dadger is False:
            self.__read_dadger = True
            try:
                caminho = pathlib.Path(self.__path).joinpath(
                    self.arquivos.dadger
                )
                script = pathlib.Path(Settings.installdir).joinpath(
                    Settings.encoding_script
                )
                await converte_codificacao(caminho, script)
                Log.log().info(f"Lendo arquivo {self.arquivos.dadger}")
                self.__dadger = Dadger.le_arquivo(
                    self.__path, self.arquivos.dadger
                )
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.dadger}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do {self.arquivos.dadger}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__dadger

    def set_dadger(self, d: Dadger) -> HTTPResponse:
        try:
            d.escreve_arquivo(self.__path, self.arquivos.dadger)
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    async def get_dadgnl(self) -> Union[DadGNL, HTTPResponse]:
        if self.__read_dadgnl is False:
            self.__read_dadgnl = True
            try:
                caminho = pathlib.Path(self.__path).joinpath(
                    self.arquivos.dadgnl
                )
                script = pathlib.Path(Settings.installdir).joinpath(
                    Settings.encoding_script
                )
                await converte_codificacao(caminho, script)
                Log.log().info(f"Lendo arquivo {self.arquivos.dadgnl}")
                self.__dadgnl = DadGNL.le_arquivo(
                    self.__path, self.arquivos.dadgnl
                )
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.dadgnl}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do {self.arquivos.dadgnl}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__dadgnl

    def set_dadgnl(self, d: DadGNL) -> HTTPResponse:
        try:
            d.escreve_arquivo(self.__path, self.arquivos.dadgnl)
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_relato(self) -> Union[Relato, HTTPResponse]:
        if self.__read_relato is False:
            self.__read_relato = True
            try:
                Log.log().info(f"Lendo arquivo relato.{self.caso.arquivos}")
                self.__relato = Relato.le_arquivo(
                    self.__path, f"relato.{self.caso.arquivos}"
                )
            except FileNotFoundError as e:
                msg = (
                    f"Não foi encontrado o arquivo relato.{self.caso.arquivos}"
                )
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do relato.{self.caso.arquivos}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__relato

    def get_relgnl(self) -> Union[RelGNL, HTTPResponse]:
        if self.__read_relgnl is False:
            self.__read_relgnl = True
            try:
                Log.log().info(f"Lendo arquivo relgnl.{self.caso.arquivos}")
                self.__relgnl = RelGNL.le_arquivo(
                    self.__path, f"relgnl.{self.caso.arquivos}"
                )
            except FileNotFoundError as e:
                msg = (
                    f"Não foi encontrado o arquivo relgnl.{self.caso.arquivos}"
                )
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do relgnl.{self.caso.arquivos}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__relgnl

    def get_inviabunic(self) -> Union[InviabUnic, HTTPResponse]:
        if self.__read_inviabunic is False:
            self.__read_inviabunic = True
            try:
                Log.log().info(
                    f"Lendo arquivo inviab_unic.{self.caso.arquivos}"
                )
                self.__inviabunic = InviabUnic.le_arquivo(
                    self.__path, f"inviab_unic.{self.caso.arquivos}"
                )
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo inviab_unic.{self.caso.arquivos}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().info(
                    f"Erro na leitura do inviab_unic.{self.caso.arquivos}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__inviabunic

    def get_hidr(self) -> Union[Hidr, HTTPResponse]:
        if self.__read_hidr is False:
            self.__read_hidr = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.hidr}")
                self.__hidr = Hidr.le_arquivo(self.__path, self.arquivos.hidr)
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.hidr}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do {self.arquivos.hidr}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__hidr


def factory(kind: str, *args, **kwargs) -> AbstractDecompRepository:
    mapping: Dict[str, Type[AbstractDecompRepository]] = {
        "FS": RawDecompRepository
    }
    return mapping.get(kind)(*args, **kwargs)
