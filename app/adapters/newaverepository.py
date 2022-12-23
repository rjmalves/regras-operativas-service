from abc import ABC, abstractmethod
import pathlib
from typing import Dict, Optional, Union
from inewave.newave.caso import Caso
from inewave.newave.arquivos import Arquivos
from inewave.newave.dger import DGer
from inewave.newave.hidr import Hidr
from inewave.newave.confhd import Confhd
from inewave.newave.eafpast import EafPast
from inewave.newave.adterm import AdTerm
from inewave.newave.term import Term
from inewave.newave.pmo import PMO

from app.internal.settings import Settings
from app.utils.encoding import converte_codificacao
from app.utils.log import Log
from app.internal.httpresponse import HTTPResponse


class AbstractNewaveRepository(ABC):
    @property
    @abstractmethod
    def arquivos(self) -> Union[Arquivos, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def get_dger(self) -> Union[DGer, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_dger(self, d: DGer) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    def get_hidr(self) -> Union[Hidr, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def get_confhd(self) -> Union[Confhd, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_confhd(self, d: Confhd) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    def get_eafpast(self) -> Union[EafPast, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_eafpast(self, d: EafPast) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    def get_adterm(self) -> Union[AdTerm, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_adterm(self, d: AdTerm) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    def get_term(self) -> Union[Term, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_term(self, d: Term) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    def get_pmo(self) -> Union[PMO, HTTPResponse]:
        raise NotImplementedError


class RawNewaveRepository(AbstractNewaveRepository):
    def __init__(self, path: str):
        self.__path = path
        try:
            self.__caso = Caso.le_arquivo(self.__path)
        except FileNotFoundError:
            Log.log().error("Não foi encontrado o arquivo caso.dat")
        self.__arquivos: Optional[Arquivos] = None
        self.__dger: Optional[DGer] = None
        self.__read_dger = False
        self.__hidr: Optional[Hidr] = None
        self.__read_hidr = False
        self.__confhd: Optional[Confhd] = None
        self.__read_confhd = False
        self.__eafpast: Optional[EafPast] = None
        self.__read_eafpast = False
        self.__adterm: Optional[AdTerm] = None
        self.__read_adterm = False
        self.__term: Optional[Term] = None
        self.__read_term = False
        self.__pmo: Optional[PMO] = None
        self.__read_pmo = False

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

    async def get_dger(self) -> Union[DGer, HTTPResponse]:
        if self.__read_dger is False:
            self.__read_dger = True
            try:
                caminho = pathlib.Path(self.__path).joinpath(
                    self.arquivos.dger
                )
                script = pathlib.Path(Settings.installdir).joinpath(
                    Settings.encoding_script
                )
                await converte_codificacao(caminho, script)
                Log.log().info(f"Lendo arquivo {self.arquivos.dger}")
                self.__dger = DGer.le_arquivo(self.__path, self.arquivos.dger)
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.dger}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do {self.arquivos.dger}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__dger

    def set_dger(self, d: DGer) -> HTTPResponse:
        try:
            d.escreve_arquivo(self.__path, self.arquivos.dger)
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_hidr(self) -> Union[Hidr, HTTPResponse]:
        if self.__read_hidr is False:
            self.__read_hidr = True
            try:
                Log.log().info("Lendo arquivo hidr.dat")
                self.__hidr = Hidr.le_arquivo(self.__path, "hidr.dat")
            except FileNotFoundError as e:
                msg = "Não foi encontrado o arquivo hidr.dat"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error("Erro na leitura do hidr.dat: {e}")
                return HTTPResponse(code=500, detail=str(e))
        return self.__hidr

    def get_confhd(self) -> Union[Confhd, HTTPResponse]:
        if self.__read_confhd is False:
            self.__read_confhd = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.confhd}")
                self.__confhd = Confhd.le_arquivo(
                    self.__path, self.arquivos.confhd
                )
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.confhd}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do {self.arquivos.confhd}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__confhd

    def set_confhd(self, d: Confhd):
        try:
            d.escreve_arquivo(self.__path, self.arquivos.confhd)
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_eafpast(self) -> Union[EafPast, HTTPResponse]:
        if self.__read_eafpast is False:
            self.__read_eafpast = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.vazpast}")
                self.__eafpast = EafPast.le_arquivo(
                    self.__path, self.arquivos.vazpast
                )
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.vazpast}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do {self.arquivos.vazpast}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__eafpast

    def set_eafpast(self, d: EafPast):
        try:
            d.escreve_arquivo(self.__path, self.arquivos.vazpast)
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_adterm(self) -> Union[AdTerm, HTTPResponse]:
        if self.__read_adterm is False:
            self.__read_adterm = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.adterm}")
                self.__adterm = AdTerm.le_arquivo(
                    self.__path, self.arquivos.adterm
                )
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.adterm}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do {self.arquivos.adterm}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__adterm

    def set_adterm(self, d: AdTerm):
        try:
            d.escreve_arquivo(self.__path, self.arquivos.adterm)
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_term(self) -> Union[Term, HTTPResponse]:
        if self.__read_term is False:
            self.__read_term = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.term}")
                self.__term = Term.le_arquivo(self.__path, self.arquivos.term)
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.term}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do {self.arquivos.term}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__term

    def set_term(self, d: Term):
        try:
            d.escreve_arquivo(self.__path, self.arquivos.term)
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_pmo(self) -> Union[PMO, HTTPResponse]:
        if self.__read_pmo is False:
            self.__read_pmo = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.pmo}")
                self.__pmo = PMO.le_arquivo(self.__path, self.arquivos.pmo)
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.pmo}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(f"Erro na leitura do {self.arquivos.pmo}: {e}")
                return HTTPResponse(code=500, detail=str(e))
        return self.__pmo


def factory(kind: str, *args, **kwargs) -> AbstractNewaveRepository:
    mappings: Dict[str, AbstractNewaveRepository] = {
        "FS": RawNewaveRepository,
    }
    return mappings[kind](*args, **kwargs)
