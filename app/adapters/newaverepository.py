from abc import ABC, abstractmethod
import pathlib
from os.path import join
from typing import Dict, Optional, Union
from inewave.newave.caso import Caso
from inewave.newave.arquivos import Arquivos
from inewave.newave.dger import Dger
from inewave.newave.hidr import Hidr
from inewave.newave.confhd import Confhd
from inewave.newave.eafpast import Eafpast
from inewave.newave.adterm import Adterm
from inewave.newave.term import Term
from inewave.newave.modif import Modif
from inewave.newave.re import Re
from inewave.newave.pmo import Pmo

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
    async def get_dger(self) -> Union[Dger, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_dger(self, d: Dger) -> HTTPResponse:
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
    def get_eafpast(self) -> Union[Eafpast, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_eafpast(self, d: Eafpast) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    def get_adterm(self) -> Union[Adterm, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_adterm(self, d: Adterm) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    def get_term(self) -> Union[Term, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_term(self, d: Term) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    def get_modif(self) -> Union[Modif, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_modif(self, d: Modif) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    def get_re(self) -> Union[Re, HTTPResponse]:
        raise NotImplementedError

    @abstractmethod
    def set_re(self, d: Re) -> HTTPResponse:
        raise NotImplementedError

    @abstractmethod
    def get_pmo(self) -> Union[Pmo, HTTPResponse]:
        raise NotImplementedError


class RawNewaveRepository(AbstractNewaveRepository):
    def __init__(self, path: str):
        self.__path = path
        try:
            self.__caso = Caso.read(join(self.__path, "caso.dat"))
        except FileNotFoundError:
            Log.log().error("Não foi encontrado o arquivo caso.dat")
        self.__arquivos: Optional[Arquivos] = None
        self.__dger: Optional[Dger] = None
        self.__read_dger = False
        self.__hidr: Optional[Hidr] = None
        self.__read_hidr = False
        self.__confhd: Optional[Confhd] = None
        self.__read_confhd = False
        self.__eafpast: Optional[Eafpast] = None
        self.__read_eafpast = False
        self.__adterm: Optional[Adterm] = None
        self.__read_adterm = False
        self.__term: Optional[Term] = None
        self.__read_term = False
        self.__modif: Optional[Modif] = None
        self.__read_modif = False
        self.__re: Optional[Re] = None
        self.__read_re = False
        self.__pmo: Optional[Pmo] = None
        self.__read_pmo = False

    @property
    def arquivos(self) -> Union[Arquivos, HTTPResponse]:
        if self.__arquivos is None:
            try:
                self.__arquivos = Arquivos.read(
                    join(self.__path, self.__caso.arquivos)
                )
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.__caso.arquivos}"
                Log.log().error(msg)
                return HTTPResponse(code=404, detail=msg)
        return self.__arquivos

    async def get_dger(self) -> Union[Dger, HTTPResponse]:
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
                self.__dger = Dger.read(join(self.__path, self.arquivos.dger))
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.dger}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do {self.arquivos.dger}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__dger

    def set_dger(self, d: Dger) -> HTTPResponse:
        try:
            d.write(join(self.__path, self.arquivos.dger))
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_hidr(self) -> Union[Hidr, HTTPResponse]:
        if self.__read_hidr is False:
            self.__read_hidr = True
            try:
                Log.log().info("Lendo arquivo hidr.dat")
                self.__hidr = Hidr.read(join(self.__path, "hidr.dat"))
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
                self.__confhd = Confhd.read(
                    join(self.__path, self.arquivos.confhd)
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
            d.write(join(self.__path, self.arquivos.confhd))
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_eafpast(self) -> Union[Eafpast, HTTPResponse]:
        if self.__read_eafpast is False:
            self.__read_eafpast = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.vazpast}")
                self.__eafpast = Eafpast.read(
                    join(self.__path, self.arquivos.vazpast)
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

    def set_eafpast(self, d: Eafpast):
        try:
            d.write(join(self.__path, self.arquivos.vazpast))
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_adterm(self) -> Union[Adterm, HTTPResponse]:
        if self.__read_adterm is False:
            self.__read_adterm = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.adterm}")
                self.__adterm = Adterm.read(
                    join(self.__path, self.arquivos.adterm)
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

    def set_adterm(self, d: Adterm):
        try:
            d.write(join(self.__path, self.arquivos.adterm))
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_term(self) -> Union[Term, HTTPResponse]:
        if self.__read_term is False:
            self.__read_term = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.term}")
                self.__term = Term.read(join(self.__path, self.arquivos.term))
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
            d.write(join(self.__path, self.arquivos.term))
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_modif(self) -> Union[Modif, HTTPResponse]:
        if self.__read_modif is False:
            self.__read_modif = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.modif}")
                self.__modif = Modif.read(
                    join(self.__path, self.arquivos.modif)
                )
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.modif}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(
                    f"Erro na leitura do {self.arquivos.modif}: {e}"
                )
                return HTTPResponse(code=500, detail=str(e))
        return self.__modif

    def set_modif(self, d: Modif):
        try:
            d.write(join(self.__path, self.arquivos.modif))
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_re(self) -> Union[Re, HTTPResponse]:
        if self.__read_re is False:
            self.__read_re = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.re}")
                self.__re = Re.read(join(self.__path, self.arquivos.re))
            except FileNotFoundError as e:
                msg = f"Não foi encontrado o arquivo {self.arquivos.re}"
                return HTTPResponse(code=404, detail=msg)
            except Exception as e:
                Log.log().error(f"Erro na leitura do {self.arquivos.re}: {e}")
                return HTTPResponse(code=500, detail=str(e))
        return self.__re

    def set_re(self, d: Re):
        try:
            d.write(join(self.__path, self.arquivos.re))
            return HTTPResponse(code=200, detail="")
        except Exception as e:
            return HTTPResponse(code=500, detail=str(e))

    def get_pmo(self) -> Union[Pmo, HTTPResponse]:
        if self.__read_pmo is False:
            self.__read_pmo = True
            try:
                Log.log().info(f"Lendo arquivo {self.arquivos.pmo}")
                self.__pmo = Pmo.read(join(self.__path, self.arquivos.pmo))
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
