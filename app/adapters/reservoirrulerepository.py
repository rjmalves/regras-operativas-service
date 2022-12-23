from abc import ABC, abstractmethod
from typing import Dict, List, Union, Callable
import pandas as pd
from idecomp.decomp.dadger import Dadger
from idecomp.decomp.modelos.dadgnl import NL, GL

from app.models.program import Program
from app.internal.httpresponse import HTTPResponse
from app.models.chainingresult import ChainingResult
from app.models.chainingvariable import ChainingVariable
from app.services.unitofwork import AbstractUnitOfWork
from app.utils.log import Log


class AbstractChainingRepository(ABC):
    """ """

    async def chain(
        self,
        variable: ChainingVariable,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        RULES: Dict[ChainingVariable, Callable] = {
            ChainingVariable.VARM: self.chain_varm,
            ChainingVariable.TVIAGEM: self.chain_tviagem,
            ChainingVariable.GNL: self.chain_gnl,
            ChainingVariable.ENA: self.chain_ena,
        }
        f = RULES.get(variable)
        if f is None:
            return HTTPResponse(code=404, detail=f"{variable} not supported")
        return await f(sources_uow, destination_uow)

    @abstractmethod
    async def chain_varm(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        pass

    @abstractmethod
    async def chain_tviagem(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        pass

    @abstractmethod
    async def chain_gnl(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        pass

    @abstractmethod
    async def chain_ena(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        pass


class NEWAVEChainingRepository(AbstractChainingRepository):
    """ """

    async def chain_varm(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        def __numero_uhe_decomp(numero_newave: int) -> int:
            mapa_ficticias_NW_DC = {
                318: 122,
                319: 57,
                294: 162,
                295: 156,
                308: 155,
                298: 148,
                292: 252,
                302: 261,
                303: 257,
                306: 253,
            }
            if numero_newave in mapa_ficticias_NW_DC.keys():
                return mapa_ficticias_NW_DC[numero_newave]
            else:
                return numero_newave

        def __coluna_para_encadear() -> str:
            # TODO - voltar a suportar caso de NW semanal
            # if self._caso_atual.revisao == 0:
            if True:
                return "Estágio 1"
            else:
                return list(volumes.columns)[-2]

        def __encadeia_ilha_solteira_equiv(
            volumes: pd.DataFrame, usinas: pd.DataFrame
        ) -> pd.DataFrame:
            vol = float(
                volumes.loc[volumes["Número"] == 44, __coluna_para_encadear()]
            )
            Log.log().info(f"Caso especial de I. Solteira Equiv: {vol} %")
            usinas.loc[usinas["Número"] == 34, "Volume Inicial"] = vol
            usinas.loc[usinas["Número"] == 43, "Volume Inicial"] = vol
            results.append(ChainingResult(id=hidr.at[34, "Nome"], value=vol))
            results.append(ChainingResult(id=hidr.at[43, "Nome"], value=vol))
            return usinas

        def __correcao_serra_mesa_ficticia(vol: float) -> float:
            return min([100.0, vol / 0.55])

        def __separou_ilha_solteira_equiv(
            volumes: pd.DataFrame, usinas: pd.DataFrame
        ) -> bool:
            # Saber se tem I. Solteira Equiv. no DECOMP mas tem as
            # usinas separadas no NEWAVE
            usinas_newave = usinas["Número"].tolist()
            usinas_decomp = volumes["Número"].tolist()
            return all(
                [
                    44 not in usinas_newave,
                    43 in usinas_newave,
                    34 in usinas_newave,
                    44 in usinas_decomp,
                    43 not in usinas_decomp,
                    34 not in usinas_decomp,
                ]
            )

        def __interpola_volume() -> float:
            # TODO - implementar para maior precisão
            pass

        SERRA_MESA_FICT_DC = 251
        SERRA_MESA_FICT_NW = 291

        decomps_uow = [s for s in sources_uow if s.program == Program.DECOMP]
        if len(decomps_uow) == 0:
            return HTTPResponse(
                code=422, detail=f"must have at least 1 DECOMP source"
            )
        last_decomp_uow = decomps_uow[-1]

        Log.log().info("Encadeando VARM - DECOMP -> NEWAVE")
        with last_decomp_uow:
            relato = last_decomp_uow.files.get_relato()
        if isinstance(relato, HTTPResponse):
            return relato

        volumes = relato.volume_util_reservatorios
        with destination_uow:
            hidr = destination_uow.files.get_hidr()
            confhd = destination_uow.files.get_confhd()
        if isinstance(confhd, HTTPResponse):
            return confhd
        if isinstance(hidr, HTTPResponse):
            return hidr

        hidr = hidr.cadastro
        usinas = confhd.usinas

        results: List[ChainingResult] = []
        # Atualiza cada armazenamento
        for _, linha in usinas.iterrows():
            num = linha["Número"]
            num_dc = __numero_uhe_decomp(num)
            # Confere se tem o reservatório
            if num_dc not in set(volumes["Número"]):
                continue
            vol = float(
                volumes.loc[
                    volumes["Número"] == num_dc, __coluna_para_encadear()
                ]
            )
            if num_dc == SERRA_MESA_FICT_DC:
                vf = __correcao_serra_mesa_ficticia(vol)
                num_nw = SERRA_MESA_FICT_NW
                usinas.loc[usinas["Número"] == num_nw, "Volume Inicial"] = vf
                results.append(
                    ChainingResult(id=hidr.at[num_nw, "Nome"], value=vf)
                )

            usinas.loc[usinas["Número"] == num, "Volume Inicial"] = vol
            results.append(ChainingResult(id=hidr.at[num, "Nome"], value=vol))

        # Trata o caso de I. Solteira Equiv.
        if __separou_ilha_solteira_equiv(volumes, usinas):
            usinas = __encadeia_ilha_solteira_equiv(volumes, usinas)

        with destination_uow:
            res = destination_uow.files.set_confhd(confhd)
            if res.code != 200:
                return res

        return results

    async def chain_tviagem(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        return HTTPResponse(code=405, detail="TVIAGEM not allowed for NEWAVE")

    async def chain_gnl(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        return HTTPResponse(code=501, detail="GNL not implemented for NEWAVE")

    async def chain_ena(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        return HTTPResponse(code=501, detail="ENA not implemented for NEWAVE")


class DECOMPChainingRepository(AbstractChainingRepository):
    """ """

    async def chain_varm(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        decomps_uow = [s for s in sources_uow if s.program == Program.DECOMP]
        if len(decomps_uow) == 0:
            return HTTPResponse(
                code=422, detail=f"must have at least 1 DECOMP source"
            )
        last_decomp_uow = decomps_uow[-1]
        Log.log().info("Encadeando VARM - DECOMP -> DECOMP")

        def __separou_ilha_solteira_equiv(
            volumes: pd.DataFrame, dadger: Dadger
        ) -> bool:
            # Saber se tem I. Solteira Equiv. no DECOMP mas tem as
            # usinas separadas no próximo DECOMP
            vols_relato = volumes["Número"].tolist()

            existe_equiv_relato = 44 in vols_relato
            existem_separadas_relato = all(
                [34 in vols_relato, 43 in vols_relato]
            )
            existe_equiv_dadger = dadger.uh(44) is not None
            existem_separadas_dadger = (dadger.uh(34) is not None) and (
                dadger.uh(43) is not None
            )
            return all(
                [
                    existe_equiv_relato,
                    not existem_separadas_relato,
                    not existe_equiv_dadger,
                    existem_separadas_dadger,
                ]
            )

        def __encadeia_ilha_solteira_equiv(
            volumes: pd.DataFrame, dadger: Dadger
        ):
            vol = float(volumes.loc[volumes["Número"] == 44, "Estágio 1"])
            Log.log().info(f"Caso especial de I. Solteira Equiv: {vol} %")
            dadger.uh(34).volume_inicial = vol
            dadger.uh(43).volume_inicial = vol
            results.append(ChainingResult(id=hidr.at[34, "Nome"], value=vol))
            results.append(ChainingResult(id=hidr.at[43, "Nome"], value=vol))

        with last_decomp_uow:
            relato = last_decomp_uow.files.get_relato()
        if isinstance(relato, HTTPResponse):
            return relato

        with destination_uow:
            dadger = await destination_uow.files.get_dadger()
            hidr = destination_uow.files.get_hidr()
        if isinstance(dadger, HTTPResponse):
            return dadger
        if isinstance(hidr, HTTPResponse):
            return hidr

        hidr = hidr.cadastro
        volumes = relato.volume_util_reservatorios
        results: List[ChainingResult] = []
        # Encadeia cada armazenamento
        for _, linha in volumes.iterrows():
            num = linha["Número"]

            # Caso especial de I. Solteira Equiv.
            if num == 44 and __separou_ilha_solteira_equiv(volumes, dadger):
                __encadeia_ilha_solteira_equiv(volumes, dadger)
                continue

            vol = float(volumes.loc[volumes["Número"] == num, "Estágio 1"])
            dadger.uh(num).volume_inicial = vol
            results.append(ChainingResult(id=hidr.at[num, "Nome"], value=vol))

        with destination_uow:
            res = destination_uow.files.set_dadger(dadger)
            if res.code != 200:
                return res

        return results

    async def chain_tviagem(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        def __codigos_usinas_tviagem() -> List[int]:
            return [156, 162]

        decomps_uow = [s for s in sources_uow if s.program == Program.DECOMP]
        if len(decomps_uow) == 0:
            return HTTPResponse(
                code=422, detail=f"must have at least 1 DECOMP source"
            )
        last_decomp_uow = decomps_uow[-1]
        Log.log().info("Encadeando TVIAGEM - DECOMP -> DECOMP")
        with last_decomp_uow:
            dadger_ant = await last_decomp_uow.files.get_dadger()
            relato = last_decomp_uow.files.get_relato()
        if isinstance(dadger_ant, HTTPResponse):
            return dadger_ant
        if isinstance(relato, HTTPResponse):
            return relato
        with destination_uow:
            dadger = await destination_uow.files.get_dadger()
            hidr = destination_uow.files.get_hidr().cadastro
        if isinstance(dadger, HTTPResponse):
            return dadger
        if isinstance(hidr, HTTPResponse):
            return hidr

        relatorio = relato.relatorio_operacao_uhe
        results: List[ChainingResult] = []
        # Encadeia cada tempo de viagem
        for codigo in __codigos_usinas_tviagem():
            # Extrai o Qdef do relato
            qdef = float(
                relatorio.loc[
                    (relatorio["Estágio"] == 1)
                    & (relatorio["Código"] == codigo),
                    "Qdef (m3/s)",
                ]
            )
            # Atualiza os tempos de viagem no dadger
            vi = dadger_ant.vi(codigo)
            dadger.vi(codigo).vazoes = [qdef] + vi.vazoes[:-1]
            results.append(
                ChainingResult(id=hidr.at[codigo, "Nome"], value=qdef)
            )

        with destination_uow:
            res = destination_uow.files.set_dadger(dadger)
            if res.code != 200:
                return res

        return results

    async def chain_gnl(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:

        decomps_uow = [s for s in sources_uow if s.program == Program.DECOMP]
        if len(decomps_uow) == 0:
            return HTTPResponse(
                code=422, detail=f"must have at least 1 DECOMP source"
            )
        last_decomp_uow = decomps_uow[-1]
        Log.log().info("Encadeando GNL - DECOMP -> DECOMP")

        with last_decomp_uow:
            dad_anterior = await last_decomp_uow.files.get_dadgnl()
            rel = last_decomp_uow.files.get_relgnl()
        if isinstance(dad_anterior, HTTPResponse):
            return dad_anterior
        if isinstance(rel, HTTPResponse):
            return rel

        with destination_uow:
            dad = await destination_uow.files.get_dadgnl()
        if isinstance(dad, HTTPResponse):
            return dad

        cods = rel.usinas_termicas["Código"].unique()
        usinas = rel.usinas_termicas["Usina"].unique()
        mapa_codigo_usina = {c: u for c, u in zip(cods, usinas)}

        registros_nl: List[NL] = dad.nl()
        codigos = [r.codigo for r in registros_nl]
        registros: List[GL] = dad.gl()
        registros_anteriores: List[GL] = dad_anterior.gl()
        results: List[ChainingResult] = []
        for c in codigos:
            # Para cada semana i (exceto a última), o registro GL do DadGNL do
            # caso atual deve ter o valor do respectivo registro GL do DadGNL
            # do caso anterior na semana i + 1
            registros_usina = [r for r in registros if r.codigo == c]
            registros_usina_anterior = [
                r for r in registros_anteriores if r.codigo == c
            ]
            # Se a usina não existia no deck anterior, ignora
            if len(registros_usina_anterior) == 0:
                continue
            cols_despacho = [f"Despacho Pat. {i}" for i in [1, 2, 3]]
            for r in registros_usina:
                # Para a última semana, o registro GL do DadGNL atual deve vir
                # do RelGNL do caso anterior, onde a semana de início tenha o
                # mesmo valor.
                if r == registros_usina[-1]:
                    op = rel.relatorio_operacao_termica
                    data = (
                        r.data_inicio[:2]
                        + "/"
                        + r.data_inicio[2:4]
                        + "/"
                        + r.data_inicio[4:]
                    )
                    # Procura pela linha em op filtrando por nome, data
                    # e pegando as colunas dos despachos
                    nome = mapa_codigo_usina[c]
                    filtro = (op["Usina"] == nome) & (
                        op["Início Semana"] == data
                    )
                    geracoes = op.loc[filtro, cols_despacho].to_numpy()
                    r.geracoes = [g for g in geracoes[0]]
                    results.append(ChainingResult(id=nome, value=geracoes[-1]))
                else:
                    # Procura pelo registro anterior com a mesma data
                    reg_ant = [
                        ra
                        for ra in registros_usina_anterior
                        if ra.data_inicio == r.data_inicio
                    ][0]
                    r.geracoes = reg_ant.geracoes

        with destination_uow:
            res = destination_uow.files.set_dadgnl(dad)
            if res.code != 200:
                return res

        return results

    async def chain_ena(
        self,
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ChainingResult], HTTPResponse]:
        return HTTPResponse(code=405, detail="ENA not allowed for DECOMP")


from app.models.reservoirrule import ReservoirRule
from app.models.reservoirgrouprule import ReservoirGroupRule


class AbstractReservoirRuleRepository:
    def regras_mes(
        self, rules: List[ReservoirRule], month: int
    ) -> List[ReservoirRule]:
        return list(set([r for r in rules if r.month == month]))

    def converte_regra_hm3(
        self, rule: ReservoirRule, uheTable: pd.DataFrame
    ) -> ReservoirRule:
        convertedRule = ReservoirRule(
            rule.reservoirCode,
            rule.uheCode,
            rule.constraintType,
            rule.month,
            0.0,
            0.0,
            0.0,
            0.0,
            rule.frequency,
            rule.label,
        )
        vmin = uheTable.at[rule.reservoirCode, "Volume Mínimo"]
        vmax = uheTable.at[rule.reservoirCode, "Volume Máximo"]

        vutil = vmax - vmin
        convertedRule.minVolume = vmin + vutil * rule.minVolume / 100.0
        convertedRule.maxVolume = vmin + vutil * rule.maxVolume / 100.0
        return convertedRule

    def converte_volumes_relato_hm3(
        self, resultTable: pd.DataFrame, uheTable: pd.DataFrame
    ):
        convertedTable = resultTable.copy()
        stageCols = ["Inicial"] + [
            c for c in convertedTable.columns if "Estágio" in c
        ]
        for _, line in resultTable.iterrows():
            vmin = uheTable.at[int(line["Número"]), "Volume Mínimo"]
            vmax = uheTable.at[int(line["Número"]), "Volume Máximo"]
            vutil = vmax - vmin
            for c in stageCols:
                v = float(line[c]) * vutil / 100.0 + vmin
                convertedTable.loc[
                    convertedTable["Número"] == int(line["Número"]), c
                ] = v
        return convertedTable

    def agrupa_usinas_defluencia(
        self, rules: List[ReservoirRule]
    ) -> List[ReservoirGroupRule]:
        # TODO - PREMISSA:
        # Assume-se que os reservatórios que compõe o equivalente
        # para cálculo do limite de defluência tem os mesmos limites
        # superiores e inferiores de defluência.
        groupedRules: List[ReservoirRule] = []
        uhes = list(set([r.uheCode for r in rules]))
        for u in uhes:
            uheLabels = list(set([r.label for r in rules if r.uheCode == u]))
            for f in uheLabels:
                frequencies = list(
                    set(
                        [
                            r.frequency
                            for r in rules
                            if r.uheCode == u and r.label == f
                        ]
                    )
                )
                for p in frequencies:
                    uheRules = ReservoirGroupRule(
                        reservoirCodes=[],
                        uheCode=u,
                        constraintType="QDEF",
                        month=0,
                        minVolume=0.0,
                        maxVolume=0.0,
                        minLimit=0.0,
                        maxLimit=0.0,
                        frequency=p,
                        label=f,
                    )
                    singleRules = [
                        r
                        for r in rules
                        if r.uheCode == u and r.label == f and r.frequency == p
                    ]
                    for r in singleRules:
                        uheRules.reservoirCodes.append(r.reservoirCode)
                        uheRules.minVolume += r.minVolume
                        uheRules.maxVolume += r.maxVolume
                        uheRules.minLimit = r.minLimit
                        uheRules.maxLimit = r.maxLimit
                        uheRules.month = r.month
                    uheRules.reservoirCodes = list(
                        set(uheRules.reservoirCodes)
                    )
                    groupedRules.append(uheRules)
        return groupedRules

    @abstractmethod
    def apply(
        self,
        rules: List[ReservoirRule],
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ReservoirGroupRule], HTTPResponse]:
        pass


class NEWAVEReservoirRuleRepository(AbstractReservoirRuleRepository):
    """ """

    def apply(
        self,
        rules: List[ReservoirRule],
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ReservoirGroupRule], HTTPResponse]:
        pass


class DECOMPReservoirRuleRepository(AbstractReservoirRuleRepository):
    """ """

    def apply(
        self,
        rules: List[ReservoirRule],
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ReservoirGroupRule], HTTPResponse]:
        pass


class AplicadorRegrasReservatoriosNEWAVE(AplicadorRegrasReservatorios):
    def __init__(self, caso: Caso) -> None:
        super().__init__(caso)

    MAPA_FICTICIAS_MODIF: Dict[int, List[int]] = {
        156: [156, 295],
        178: [172, 176, 178],
    }
    MAPA_FICTICIAS_RE: Dict[int, List[int]] = {
        156: [156],
        178: [172, 176, 178],
    }

    def identifica_regra_ativa(
        self,
        regras: List[RegraReservatorio],
        codigo_usina: int,
        volumes: pd.DataFrame,
        estagio: int,
    ) -> Optional[RegraReservatorio]:

        codigo_reservatorio = next(
            r.codigo_reservatorio
            for r in regras
            if r.codigo_usina == codigo_usina
        )
        volume_total = float(
            volumes.loc[
                volumes["Número"].isin(codigo_reservatorio),
                f"Estágio {estagio}",
            ].sum()
        )
        try:
            regra = None
            for r in regras:
                if all(
                    [
                        r.codigo_usina == codigo_usina,
                        r.volume_minimo
                        <= float(volume_total)
                        < r.volume_maximo,
                    ]
                ):
                    regra = r
                    break
            if regra is None:
                raise StopIteration()
        except StopIteration:
            Log.log().warning(
                "Não foi encontrada regra de operação ativa "
                + f"para a usina {codigo_usina} "
                + f"(reservatórios {codigo_reservatorio}) "
                + f"no volume {float(volume_total)}"
            )
            regra = None
        return regra

    def regras_estagios(
        self,
        regras: List[RegraReservatorio],
        mapa_estagio_dia: Dict[int, date],
    ) -> Dict[int, List[RegraReservatorio]]:
        regras_mapeadas: Dict[int, List[RegraReservatorio]] = {}
        for estagio, dia_fim in mapa_estagio_dia.items():
            regras_mapeadas[estagio] = list(
                set([r for r in regras if r.mes == dia_fim.month])
            )
        return regras_mapeadas

    def identifica_regras_ativas(
        self,
        regras: List[RegraReservatorio],
        volumes_hm3: pd.DataFrame,
    ) -> Dict[int, List[RegraReservatorio]]:
        # Obtém os volumes
        regras_ativas_estagios: Dict[int, List[RegraReservatorio]] = {}
        estagio = int(
            [c for c in list(volumes_hm3.columns) if "Estágio" in c][-1].split(
                "Estágio"
            )[1]
        )
        # Obtém as regras ativas para cada usina
        usinas_com_restricao = list(set([r.codigo_usina for r in regras]))
        regras_ativas: List[RegraReservatorio] = []
        for u in usinas_com_restricao:
            regra_estagio = self.identifica_regra_ativa(
                regras, u, volumes_hm3, estagio
            )
            if regra_estagio is not None:
                regras_ativas.append(regra_estagio)
        regras_ativas_estagios[estagio] = regras_ativas
        return regras_ativas_estagios

    def obtem_ghmax_usina(
        self, codigo: int, qdef: float, hidr: pd.DataFrame
    ) -> float:
        def aplica_polinomio(coeficientes: List, vol: float) -> float:
            return sum([c * vol**i for i, c in enumerate(coeficientes)])

        # Localiza os dados de interesse da usina
        volmin = float(hidr.loc[codigo, "Volume Mínimo"])
        volmax = float(hidr.loc[codigo, "Volume Máximo"])
        volutil = volmax - volmin
        vol65 = volmin + 0.65 * volutil
        hjus = float(hidr.loc[codigo, "Canal de Fuga Médio"])
        hmon = aplica_polinomio(
            [float(hidr.loc[codigo, f"A{i} CV"]) for i in range(5)], vol65
        )
        perdas = float(hidr.loc[codigo, "Perdas"])
        hliq = hmon - hjus - perdas
        prod = float(hidr.loc[codigo, "Produtibilidade Específica"])
        prod_media = prod * hliq
        return prod_media * qdef

    def aplica_regra_qdef_modif(
        self,
        regra: RegraReservatorio,
        modif: Modif,
        hidr: pd.DataFrame,
        codigo: int = None,
    ):
        if codigo is None:
            codigo = regra.codigo_usina
        # Se a regra não tem limite mínimo, ignora
        if regra.limite_minimo is None:
            return

        modif_usina = modif.modificacoes_usina(codigo)
        # Se a usina em questão não é modificada, cria uma modificação nova
        if modif_usina is None:
            nova_usina = USINA()
            nova_usina.codigo = codigo
            nova_usina.nome = str(hidr.loc[codigo, "Nome"])
            modif.append_registro(nova_usina)
            Log.log().info(f"Criando novo registro USINA {codigo}")
        # Obtém o registro que modifica a usina
        usina: USINA = modif.usina(codigo=codigo)

        vazmint_existentes = [m for m in modif_usina if isinstance(m, VAZMINT)]
        vazmin_existentes = [m for m in modif_usina if isinstance(m, VAZMIN)]
        Log.log().info(
            f"Existem {len(vazmint_existentes)} VAZMINT"
            + f" para a usina {codigo}"
        )
        Log.log().info(
            f"Existem {len(vazmin_existentes)} VAZMIN"
            + f" para a usina {codigo}"
        )
        # Guarda a vazão do primeiro VAZMINT que tenha início após os
        # 2 primeiros meses. Se não existir, procura VAZMIN. Por último,
        # procura no HIDR
        data_caso = date(self._caso.ano, self._caso.mes, 1)
        ultima_vazao = 0.0
        if len(vazmint_existentes) > 0:
            for m in vazmint_existentes:
                ultima_vazao = m.vazao
                data_inicio = date(m.ano, m.mes, 1)
                if data_inicio >= data_caso + relativedelta(months=+2):
                    break
            if ultima_vazao == 0:
                ultima_vazao = float(hidr.loc[codigo, "Vazão Mínima"])
        elif len(vazmin_existentes) > 0:
            ultima_vazao = vazmin_existentes[-1].vazao
        else:
            ultima_vazao = float(hidr.loc[codigo, "Vazão Mínima"])
        Log.log().info(f"Última vazão = {ultima_vazao}")
        for m in vazmint_existentes:
            # Deleta os VAZMINT que iniciem nos 2 primeiros meses
            data_inicio = date(m.ano, m.mes, 1)
            if data_inicio < data_caso + relativedelta(months=+2):
                modif.deleta_registro(m)
        # Cria os VAZMINT
        # - O primeiro é válido para os 2 primeiros meses
        novo_vazmint = VAZMINT()
        novo_vazmint.mes = self._caso.mes
        novo_vazmint.ano = self._caso.ano
        novo_vazmint.vazao = regra.limite_minimo
        Log.log().info(
            f"Criando VAZMINT = {self._caso.mes}"
            + f" {self._caso.ano} {regra.limite_minimo}"
        )
        modif.cria_registro(usina, novo_vazmint)
        # - O segundo é para retornar ao valor anterior
        fim_vazmint = date(
            year=self._caso.ano, month=self._caso.mes, day=1
        ) + relativedelta(months=+2)
        prox_vazmint = VAZMINT()
        prox_vazmint.mes = fim_vazmint.month
        prox_vazmint.ano = fim_vazmint.year
        prox_vazmint.vazao = ultima_vazao
        Log.log().info(
            f"Criando VAZMINT = {fim_vazmint.month}"
            + f" {fim_vazmint.year} {ultima_vazao}"
        )
        modif.cria_registro(novo_vazmint, prox_vazmint)

    def aplica_regra_qdef_re(
        self,
        regra: RegraReservatorio,
        re: RE,
        hidr: pd.DataFrame,
        codigo: int = None,
    ):
        if codigo is None:
            codigo = regra.codigo_usina
        # Se não existe um conjunto com a usina em questão, cria.
        cols_usinas = [f"Usina {i}" for i in range(1, 11)]
        df_conjuntos = re.usinas_conjuntos
        conjuntos = list(df_conjuntos["Conjunto"].unique())
        if codigo not in df_conjuntos[cols_usinas].to_numpy():
            Log.log().info(f"Criando conjunto com usina {codigo}")
            num_conjunto = max(conjuntos) + 1
            novo_conjunto = {
                **{"Conjunto": [num_conjunto]},
                **{c: [0] for c in cols_usinas},
            }
            novo_conjunto["Usina 1"] = [codigo]
            re.usinas_conjuntos = df_conjuntos.append(
                pd.DataFrame(data=novo_conjunto), ignore_index=True
            )
            df_conjuntos = re.usinas_conjuntos
        # Senão, identifica.
        num_conjunto = next(
            int(linha["Conjunto"])
            for _, linha in df_conjuntos.iterrows()
            if codigo in linha[cols_usinas].to_numpy()
        )
        # Cria as restrições para o conjunto em questão, nos 2 primeiros
        # meses do horizonte
        mes_inicial = date(year=self._caso.ano, month=self._caso.mes, day=1)
        mes_final = mes_inicial + relativedelta(months=+1)
        # Deleta as restrições do conjunto em questão, se existirem e começarem
        # em algum dos 2 primeiros meses
        restricoes = re.restricoes
        indices_restricoes = restricoes.loc[
            (restricoes["Conjunto"] == num_conjunto)
            & (
                (restricoes["Mês Início"] == mes_inicial.month)
                | (restricoes["Mês Início"] == mes_final.month)
            )
            & (
                (restricoes["Ano Início"] == mes_inicial.year)
                | (restricoes["Ano Início"] == mes_final.year)
            ),
            :,
        ].index
        restricoes = restricoes.drop(index=indices_restricoes)

        # Se a regra não tem limite máximo, ignora
        qdef = regra.limite_maximo
        if qdef is None:
            return
        nova_restricao = {
            "Conjunto": [num_conjunto],
            "Mês Início": [mes_inicial.month],
            "Ano Início": [mes_inicial.year],
            "Mês Fim": [mes_final.month],
            "Ano Fim": [mes_final.year],
            "Flag P": [0],
            "Restrição": [self.obtem_ghmax_usina(codigo, qdef, hidr)],
            "Motivo": ["REGRA ANA"],
        }
        re.restricoes = restricoes.append(
            pd.DataFrame(data=nova_restricao), ignore_index=True
        )

    def aplica_regra(
        self,
        regra: RegraReservatorio,
        hidr: pd.DataFrame,
        modif: Modif,
        re: RE,
    ) -> bool:
        if regra.tipo_restricao == "QDEF":
            Log.log().info(
                f"Aplicando regra: {str(regra)} no mês {self._caso.mes}"
            )
            # No caso de existirem, aplica também nas fictícias
            # Aplica a restrição da defluência mínima, se houver,
            # no modif.dat
            mapa_modif = (
                AplicadorRegrasReservatoriosNEWAVE.MAPA_FICTICIAS_MODIF
            )
            if regra.limite_minimo is not None:
                if regra.codigo_usina in mapa_modif.keys():
                    for codigo in mapa_modif[regra.codigo_usina]:
                        self.aplica_regra_qdef_modif(
                            regra, modif, hidr, codigo=codigo
                        )
                else:
                    self.aplica_regra_qdef_modif(regra, modif, hidr)
            # Aplica a restrição da defluência máxima, se houver,
            # no re.dat
            mapa_re = AplicadorRegrasReservatoriosNEWAVE.MAPA_FICTICIAS_RE
            if regra.limite_maximo is not None:
                if regra.codigo_usina in mapa_re.keys():
                    for codigo in mapa_re[regra.codigo_usina]:
                        self.aplica_regra_qdef_re(
                            regra, re, hidr, codigo=codigo
                        )
                else:
                    self.aplica_regra_qdef_re(regra, re, hidr)
        return True

    def aplica_regras(
        self,
        casos_anteriores: List[Caso],
        regras_operacao: List[RegraReservatorio],
    ) -> bool:
        # Obtém o último DECOMP executado no mês anterior
        try:
            mes_anterior = 12 if self._caso.mes == 1 else self._caso.mes - 1
            ultimo_decomp = next(
                c
                for c in reversed(casos_anteriores)
                if c.programa == Programa.DECOMP and c.mes == mes_anterior
            )
        except StopIteration:
            Log.log().info(
                f"Caso {self._caso.nome} não possui DECOMP anterior. "
                + "Não serão aplicadas regras operativas de reservatórios."
            )
            return True

        dc_uow = dc_uow_factory("FS", ultimo_decomp.caminho)
        with dc_uow:
            relato = dc_uow.decomp.get_relato()

        # Filtra as regras de operação para o mês do caso
        regras_mes = self.regras_mes(regras_operacao, self._caso.mes)

        nw_uow = nw_uow_factory("FS", self._caso.caminho)
        with nw_uow:
            cadastro_hidr = nw_uow.newave.get_hidr().cadastro

        # Converte as regras para hm3
        regras_hm3 = [
            self.converte_regra_hm3(r, cadastro_hidr) for r in regras_mes
        ]

        # Agrupa regras por usina com defluência limitada
        regras_agrupadas = self.agrupa_usinas_defluencia(regras_hm3)

        volumes_relato_hm3 = self.converte_volumes_relato_hm3(
            relato.volume_util_reservatorios, cadastro_hidr
        )
        # Identifica as regras ativas
        regras_ativas = self.identifica_regras_ativas(
            regras_agrupadas, volumes_relato_hm3
        )

        sucessos: List[bool] = []
        # Para o NEWAVE, são sempre tomadas as regras vigentes para os
        # volumes do últimos estágio semanal do último DECOMP do mês anterior
        estagio = sorted(list(regras_ativas.keys()))[-1]
        with nw_uow:
            modif = nw_uow.newave.get_modif()
            re = nw_uow.newave.get_modif()
            for r in regras_ativas[estagio]:
                sucessos.append(self.aplica_regra(r, cadastro_hidr, modif, re))
            nw_uow.newave.set_modif(modif)
            nw_uow.newave.set_re(re)
        return all(sucessos)


class AplicadorRegrasReservatoriosDECOMP(AplicadorRegrasReservatorios):
    def __init__(self, caso: Caso) -> None:
        super().__init__(caso)

    # Override
    def identifica_regra_ativa(
        self,
        regras: List[RegraReservatorio],
        codigo_usina: int,
        volumes: pd.DataFrame,
        estagio: int,
    ) -> Optional[RegraReservatorio]:
        codigos_reservatorios = next(
            r.codigo_reservatorio
            for r in regras
            if r.codigo_usina == codigo_usina
        )
        volume_total = float(
            volumes.loc[
                volumes["Número"].isin(codigos_reservatorios),
                f"Estágio {estagio}",
            ].sum()
        )
        try:
            regra = None
            for r in regras:
                if all(
                    [
                        r.codigo_usina == codigo_usina,
                        r.volume_minimo
                        <= float(volume_total)
                        < r.volume_maximo,
                    ]
                ):
                    regra = r
                    break
            if regra is None:
                raise StopIteration()
        except StopIteration:
            Log.log().warning(
                "Não foi encontrada regra de operação ativa "
                + f"para a usina {codigo_usina} "
                + f"(reservatórios {codigos_reservatorios}) "
                + f"no volume {float(volume_total)}"
            )
            regra = None
        return regra

    def identifica_regras_ativas(
        self,
        regras: Dict[int, List[RegraReservatorio]],
        volumes_hm3: pd.DataFrame,
    ) -> Dict[int, List[RegraReservatorio]]:
        # Obtém os volumes

        regras_ativas_estagios: Dict[int, List[RegraReservatorio]] = {}
        # Obtém as regras ativas para cada usina
        for estagio, regras_estagio in regras.items():
            usinas_com_restricao = list(
                set([r.codigo_usina for r in regras_estagio])
            )
            regras_ativas: List[RegraReservatorio] = []
            for u in usinas_com_restricao:
                regra_estagio = self.identifica_regra_ativa(
                    regras[estagio], u, volumes_hm3, estagio
                )
                if regra_estagio is not None:
                    regras_ativas.append(regra_estagio)
            regras_ativas_estagios[estagio] = regras_ativas
        return regras_ativas_estagios

    def aplica_regra(
        self,
        dadger: Dadger,
        regra: RegraReservatorio,
        estagio_aplicacao: int,
    ) -> bool:
        def aplica_regra_qdef(
            regra: RegraReservatorio, dadger: Dadger, estagio: int
        ):
            # Se vai aplicar uma regra em um determinado estágio
            # acessa a restrição em todos os estágios futuros, até
            # o limite, para garantir os valore serão mantidos.
            cqs: List[CQ] = dadger.cq()
            if isinstance(cqs, CQ):
                cqs = [cqs]
            if isinstance(cqs, list):
                cqs_usina = [c for c in cqs if c.uhe == regra.codigo_usina]
                if len(cqs_usina) > 0:
                    codigos_restricoes = [cq.restricao for cq in cqs_usina]
                else:
                    codigos_restricoes = [cqs[-1].restricao + 1]
                    cqs_usinas = [CQ()]
                    cqs_usinas[0].restricao = [
                        codigos_restricoes[0],
                        1,
                        regra.codigo_usina,
                        1.0,
                        regra.tipo_restricao,
                    ]
                efs = [
                    dadger.hq(codigo=codigo).estagio_final
                    for codigo in codigos_restricoes
                ]
            else:
                for cq_usina, codigo in zip(cqs_usina, codigos_restricoes):
                    # Se não existe o registro HQ, cria, junto com um LQ
                    registros_dp = dadger.lista_registros(DP)
                    num_subsistemas = len(dadger.lista_registros(SB))
                    ef = int(len(registros_dp) / num_subsistemas)
                    Log.log().info(f"Criando HQ {codigo} - 1 {ef}")
                    hq_novo = HQ()
                    hq_novo._dados = [codigo, 1, ef]
                    lq_novo = LQ()
                    lq_novo._dados = [codigo, 1] + [
                        0,
                        99999,
                        0,
                        99999,
                        0,
                        99999,
                    ]
                    dadger.cria_registro(dadger.ev, hq_novo)
                    dadger.cria_registro(hq_novo, lq_novo)
                    dadger.cria_registro(lq_novo, cq_usina)
                efs = [
                    dadger.hq(codigo).estagio_final
                    for codigo in codigos_restricoes
                ]

            for cq_usina, codigo, ef in zip(
                cqs_usina, codigos_restricoes, efs
            ):
                for e in range(estagio, ef + 1):
                    dadger.lq(codigo, e)
                # Aplica a regra no estágio devido, se tiver limites inf/sup
                if regra.limite_minimo is not None:
                    dadger.lq(codigo, estagio).limites_inferiores = [
                        regra.limite_minimo
                    ] * 3
                if regra.limite_maximo is not None:
                    dadger.lq(codigo, estagio).limites_superiores = [
                        regra.limite_maximo
                    ] * 3

        Log.log().info(
            f"Aplicando regra: {str(regra)} no estágio {estagio_aplicacao}"
        )
        # Se ocorrer algum erro, retorna False
        if regra.tipo_restricao == "QDEF":
            aplica_regra_qdef(regra, dadger, estagio_aplicacao)
        else:
            return False
        return True

    def mapeia_semanas_dias_fim(
        self, dadger: Dadger, relato: Relato, delta_inicial: int = 0
    ) -> Dict[int, date]:
        dt = dadger.dt
        dia_inicio_caso_atual = date(dt.ano, dt.mes, dt.dia)
        num_semanas_caso_anterior = (
            len(relato.volume_util_reservatorios.columns) - 3
        )
        return {
            i
            + 1: dia_inicio_caso_atual
            - timedelta(weeks=delta_inicial, days=1)
            + timedelta(weeks=i, days=0)
            for i in range(num_semanas_caso_anterior)
        }

    def regras_estagios(
        self,
        regras: List[RegraReservatorio],
        mapa_estagio_dia: Dict[int, date],
    ) -> Dict[int, List[RegraReservatorio]]:
        regras_mapeadas: Dict[int, List[RegraReservatorio]] = {}
        for estagio, dia_fim in mapa_estagio_dia.items():
            regras_mapeadas[estagio] = list(
                set([r for r in regras if r.mes == dia_fim.month])
            )
        return regras_mapeadas

    def aplica_regras_caso(
        self,
        regras_operacao: List[RegraReservatorio],
        dadger: Dadger,
        relato: Relato,
        gap_semanas: int = 0,
        regras_mensais: bool = False,
    ) -> bool:

        # Identifica o dia de fim de cada semana do DECOMP anterior
        mapa_dias_fim = self.mapeia_semanas_dias_fim(
            dadger, relato, gap_semanas
        )
        # Se está falando de regras mensais, não consulta semana a semana
        if regras_mensais:
            ultimo_estagio = list(mapa_dias_fim.keys())[-1]
            mapa_dias_fim = {1: mapa_dias_fim[ultimo_estagio]}
        Log.log().info(
            f"Dias de fim dos estágios do DECOMP anterior: {mapa_dias_fim}"
        )

        # Filtra as regras de operação para cada estágio
        # do DECOMP anterior
        regras_estagios = self.regras_estagios(regras_operacao, mapa_dias_fim)

        # Identifica as regras ativas
        regras_ativas = self.identifica_regras_ativas(regras_estagios, relato)

        # Aplica as regras ativas
        registros_dp = dadger.dp()
        num_subsistemas = len(dadger.sb())
        num_estagios = int(len(registros_dp) / num_subsistemas)
        estagios_decomp_atual = list(range(1, num_estagios + 1))
        sucessos: List[bool] = []
        for estagio in estagios_decomp_atual:
            Log.log().info(
                f"Aplicando regras de reservatórios no estágio {estagio}"
            )
            if estagio not in regras_ativas.keys():
                estagio_aplicacao = sorted(list(regras_ativas.keys()))[-1]
            else:
                estagio_aplicacao = estagio
            for r in regras_ativas[estagio_aplicacao]:
                sucessos.append(self.aplica_regra(dadger, r, estagio))

        return all(sucessos)

    def aplica_regras(
        self,
        casos_anteriores: List[Caso],
        regras_operacao: List[RegraReservatorio],
    ) -> bool:
        regras_semanais = list(
            set([r for r in regras_operacao if r.periodicidade == "S"])
        )
        dc_uow = dc_uow_factory("FS", self._caso.caminho)
        with dc_uow:
            dadger_caso = dc_uow.decomp.get_dadger()
        try:
            ultimo_decomp = next(
                c
                for c in reversed(casos_anteriores)
                if c.programa == Programa.DECOMP
            )
            ultimo_dc_uow = dc_uow_factory("FS", ultimo_decomp.caminho)
            with ultimo_dc_uow:
                relato_ultimo_dc = ultimo_dc_uow.decomp.get_relato()
            self.aplica_regras_caso(
                regras_semanais, dadger_caso, relato_ultimo_dc
            )
        except StopIteration:
            Log.log().info(
                f"Caso {self._caso.nome} não possui DECOMP anterior. "
                + "Não serão aplicadas regras operativas de reservatórios "
                + "com periodicidade semanal."
            )

        try:
            mes_anterior = 12 if self._caso.mes == 1 else self._caso.mes - 1
            ultimo_decomp_mes_anterior = next(
                c
                for c in reversed(casos_anteriores)
                if c.programa == Programa.DECOMP and c.mes == mes_anterior
            )
            regras_mensais = list(
                set([r for r in regras_operacao if r.periodicidade == "M"])
            )
            gap_semanas = (
                len(casos_anteriores)
                - casos_anteriores.index(ultimo_decomp_mes_anterior)
                - 2
            )
            self.aplica_regras_caso(
                regras_mensais,
                dadger_caso,
                relato_ultimo_dc,
                gap_semanas,
                True,
            )
        except StopIteration:
            Log.log().info(
                f"Caso {self._caso.nome} não possui DECOMP no mês anterior. "
                + "Não serão aplicadas regras operativas de reservatórios "
                + "com periodicidade mensal."
            )

        with dc_uow:
            dc_uow.decomp.set_dadger(dadger_caso)

        return True


SUPPORTED_PROGRAMS: Dict[Program, AbstractReservoirRuleRepository] = {
    Program.NEWAVE: NEWAVEReservoirRuleRepository,
    Program.DECOMP: DECOMPReservoirRuleRepository,
}
DEFAULT = DECOMPReservoirRuleRepository


def factory(
    destination: str, *args, **kwargs
) -> AbstractReservoirRuleRepository:
    s = SUPPORTED_PROGRAMS.get(destination)
    if s is None:
        return DEFAULT(*args, **kwargs)
    return s(*args, **kwargs)
