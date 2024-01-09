from abc import abstractmethod
from typing import Dict, List, Union, Optional, Callable
import pandas as pd
from idecomp.decomp.dadger import Dadger
from idecomp.decomp.modelos.dadger import CQ, HQ, LQ
from idecomp.decomp.relato import Relato
from inewave.newave import Confhd, Modif, Re, Dger
from inewave.newave.modelos.modif import (
    USINA,
    VAZMIN,
    VAZMINT,
    TURBMINT,
    TURBMAXT,
)
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.models.program import Program
from app.models.reservoirrule import ReservoirRule
from app.models.reservoirgrouprule import ReservoirGroupRule
from app.internal.httpresponse import HTTPResponse
from app.services.unitofwork import AbstractUnitOfWork
from app.utils.log import Log


class AbstractReservoirRuleRepository:
    def regras_mes(
        self, rules: List[ReservoirRule], month: int
    ) -> List[ReservoirRule]:
        return list(set([r for r in rules if r.month == month]))

    def converte_regra_hm3(
        self, rule: ReservoirRule, uheTable: pd.DataFrame
    ) -> ReservoirRule:
        convertedRule = ReservoirRule(
            reservoirCode=rule.reservoirCode,
            uheCode=rule.uheCode,
            constraintType=rule.constraintType,
            month=rule.month,
            minLimit=rule.minLimit,
            maxLimit=rule.maxLimit,
            minVolume=0.0,
            maxVolume=0.0,
            frequency=rule.frequency,
            label=rule.label,
        )
        vmin = uheTable.at[rule.reservoirCode, "volume_minimo"]
        vmax = uheTable.at[rule.reservoirCode, "volume_maximo"]

        vutil = vmax - vmin
        convertedRule.minVolume = vmin + vutil * rule.minVolume / 100.0
        convertedRule.maxVolume = vmin + vutil * rule.maxVolume / 100.0
        return convertedRule

    def converte_regra_equiv_percent(
        self, rule: ReservoirGroupRule, uheTable: pd.DataFrame
    ) -> ReservoirGroupRule:
        convertedRule = ReservoirGroupRule(
            reservoirCodes=rule.reservoirCodes,
            uheCode=rule.uheCode,
            constraintType=rule.constraintType,
            month=rule.month,
            minLimit=rule.minLimit,
            maxLimit=rule.maxLimit,
            minVolume=0.0,
            maxVolume=0.0,
            frequency=rule.frequency,
            label=rule.label,
        )
        vmin = 0.0
        vmax = 0.0
        for code in rule.reservoirCodes:
            vmin += uheTable.at[code, "volume_minimo"]
            vmax += uheTable.at[code, "volume_maximo"]

        vutil = vmax - vmin
        convertedRule.minVolume = round(
            100 * (rule.minVolume - vmin) / vutil, 2
        )
        convertedRule.maxVolume = round(
            100 * (rule.maxVolume - vmin) / vutil, 2
        )
        return convertedRule

    def converte_volumes_relato_hm3(
        self, resultTable: pd.DataFrame, uheTable: pd.DataFrame
    ):
        convertedTable = resultTable.copy()
        stageCols = ["inicial"] + [
            c for c in convertedTable.columns if "estagio" in c
        ]
        for _, line in resultTable.iterrows():
            vmin = uheTable.at[int(line["codigo_usina"]), "volume_minimo"]
            vmax = uheTable.at[int(line["codigo_usina"]), "volume_maximo"]
            vutil = vmax - vmin
            for c in stageCols:
                v = float(line[c]) * vutil / 100.0 + vmin
                convertedTable.loc[
                    convertedTable["codigo_usina"]
                    == int(line["codigo_usina"]),
                    c,
                ] = v
        return convertedTable

    def agrupa_usinas_defluencia(
        self, rules: List[ReservoirRule]
    ) -> List[ReservoirGroupRule]:
        # TODO - PREMISSA:
        # Assume-se que os reservatórios que compõe o equivalente
        # para cálculo do limite de defluência tem os mesmos limites
        # superiores e inferiores de defluência.
        groupedRules: List[ReservoirGroupRule] = []
        uhes = list(set([r.uheCode for r in rules]))
        tipos = list(set([r.constraintType for r in rules]))

        for tipo in tipos:
            for u in uhes:
                uheLabels = list(
                    set(
                        [
                            r.label
                            for r in rules
                            if (r.uheCode == u)
                            and (r.constraintType == tipo)
                        ]
                    )
                )
                for f in uheLabels:
                    frequencies = list(
                        set(
                            [
                                r.frequency
                                for r in rules
                                if (r.uheCode == u) and (r.label == f) and (r.constraintType == tipo)
                            ]
                        )
                    )
                    for p in frequencies:
                        uheRules = ReservoirGroupRule(
                            reservoirCodes=[],
                            uheCode=u,
                            constraintType=tipo,
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
                            if r.uheCode == u
                            and r.label == f
                            and r.frequency == p
                            and r.constraintType == tipo
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
    async def apply(
        self,
        rules: List[ReservoirRule],
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ReservoirGroupRule], HTTPResponse]:
        pass


class NEWAVEReservoirRuleRepository(AbstractReservoirRuleRepository):
    """ """

    MAPA_FICTICIAS_MODIF: Dict[int, List[int]] = {
        156: [156, 295],
        178: [172, 176, 178],
    }
    MAPA_FICTICIAS_RE: Dict[int, List[int]] = {
        156: [156],
        178: [172, 176, 178],
    }

    def identify_active_rule(
        self,
        rules: List[ReservoirGroupRule],
        uheCode: int,
        volumes: pd.DataFrame,
        stage: int,
    ) -> Optional[ReservoirGroupRule]:
        reservoirCodes = next(
            r.reservoirCodes for r in rules if r.uheCode == uheCode
        )
        totalVolume = float(
            volumes.loc[
                volumes["codigo_usina"].isin(reservoirCodes),
                f"estagio_{stage}",
            ].sum()
        )
        try:
            rule = None
            for r in rules:
                if all(
                    [
                        r.uheCode == uheCode,
                        r.minVolume <= totalVolume < r.maxVolume,
                    ]
                ):
                    rule = r
                    break
            if rule is None:
                raise StopIteration()
        except StopIteration:
            Log.log().warning(
                "Não foi encontrada regra de operação ativa "
                + f"para a usina {uheCode} "
                + f"(reservatórios {reservoirCodes}) "
                + f"no volume {totalVolume}"
            )
            rule = None
        return rule

    def regras_estagios(
        self,
        rules: List[ReservoirRule],
        stageDayMap: Dict[int, datetime],
    ) -> Dict[int, List[ReservoirRule]]:
        mappedRules: Dict[int, List[ReservoirRule]] = {}
        for stage, endDay in stageDayMap.items():
            mappedRules[stage] = list(
                set([r for r in rules if r.month == endDay.month])
            )
        return mappedRules

    def identify_active_rules(
        self,
        rules: List[ReservoirGroupRule],
        uheVolumesHm3: pd.DataFrame,
    ) -> Dict[int, List[ReservoirGroupRule]]:
        # Obtém os volumes
        activeRulesByStage: Dict[int, List[ReservoirGroupRule]] = {}
        stage = int(
            [c for c in list(uheVolumesHm3.columns) if "estagio_" in c][
                -1
            ].split("estagio_")[1]
        )
        # Obtém as regras ativas para cada usina
        uhesWithRules = list(set([r.uheCode for r in rules]))
        activeRules: List[ReservoirGroupRule] = []
        for u in uhesWithRules:
            rulesInStage = self.identify_active_rule(
                rules, u, uheVolumesHm3, stage
            )
            if rulesInStage is not None:
                activeRules.append(rulesInStage)
        activeRulesByStage[stage] = activeRules
        return activeRulesByStage

    def obtem_ghmax_usina(
        self, code: int, qdef: float, hidr: pd.DataFrame
    ) -> float:
        def apply_poly(coefficients: List, vol: float) -> float:
            return sum([c * vol**i for i, c in enumerate(coefficients)])

        # Localiza os dados de interesse da usina
        volmin = hidr.at[code, "volume_minimo"]
        volmax = hidr.at[code, "volume_maximo"]
        volutil = volmax - volmin
        vol65 = volmin + 0.65 * volutil
        hjus = hidr.at[code, "canal_fuga_medio"]
        hmon = apply_poly(
            [hidr.at[code, f"a{i}_volume_cota"] for i in range(5)], vol65
        )
        losses = hidr.at[code, "perdas"]
        hliq = hmon - hjus - losses
        prod = hidr.at[code, "produtibilidade_especifica"]
        avg_prod = prod * hliq
        vazao_limitada = min([self.obtem_engolimento_usina(code, hidr), qdef])
        return avg_prod * vazao_limitada

    def obtem_engolimento_usina(self, code: int, hidr: pd.DataFrame) -> float:
        engol_usi = 0
        n_conj = hidr.at[code, "numero_conjuntos_maquinas"]
        for i in range(1, n_conj + 1):
            engol_usi += (
                hidr.at[code, f"maquinas_conjunto_{i}"]
                * hidr.at[code, f"vazao_nominal_conjunto_{i}"]
            )
        return engol_usi

    def apply_qdef_modif_rule(
        self,
        rule: ReservoirGroupRule,
        modif: Modif,
        hidr: pd.DataFrame,
        confhd: Confhd,
        dger: Dger,
        code: int = None,
    ):
        if code is None:
            code = rule.uheCode
        # Se a regra não tem limite mínimo, ignora
        if rule.minLimit is None:
            return HTTPResponse(code=200, detail="ignored")

        modifUhe = modif.modificacoes_usina(code)
        # Se a usina em questão não é modificada, cria uma modificação nova
        if modifUhe is None:
            newUhe = USINA()
            newUhe.codigo = code
            newUhe.nome = str(hidr.at[code, "nome_usina"])
            modif.data.append(newUhe)
            Log.log().info(f"Criando novo registro USINA {code}")
            confhd.usinas.loc[
                confhd.usinas["codigo_usina"] == code, "usina_modificada"
            ] = 1
            Log.log().info(f"Modificando usina {code} no confhd.dat")
        # Obtém o registro que modifica a usina
        usina: USINA = modif.usina(codigo=code)

        actualVazminT = [m for m in modifUhe if isinstance(m, VAZMINT)]
        actualVazmin = [m for m in modifUhe if isinstance(m, VAZMIN)]
        Log.log().info(
            f"Existem {len(actualVazminT)} VAZMINT" + f" para a usina {code}"
        )
        Log.log().info(
            f"Existem {len(actualVazmin)} VAZMIN" + f" para a usina {code}"
        )
        # Guarda a vazão do primeiro VAZMINT que tenha início após os
        # 2 primeiros meses. Se não existir, procura VAZMIN. Por último,
        # procura no HIDR

        caseDate = datetime(
            year=dger.ano_inicio_estudo, month=dger.mes_inicio_estudo, day=1
        )
        lastFlow = 0.0
        if len(actualVazminT) > 0:
            for m in actualVazminT:
                lastFlow = m.vazao
                startDate = m.data_inicio
                if startDate >= caseDate + relativedelta(months=+2):
                    break
            if lastFlow == 0:
                lastFlow = float(hidr.loc[code, "vazao_minima_historica"])
        elif len(actualVazmin) > 0:
            lastFlow = actualVazmin[-1].vazao
        else:
            lastFlow = hidr.at[code, "vazao_minima_historica"]
        Log.log().info(f"Última vazão = {lastFlow}")
        for m in actualVazminT:
            # Deleta os VAZMINT que iniciem nos 2 primeiros meses
            startDate = m.data_inicio
            if startDate < caseDate + relativedelta(months=+2):
                modif.data.remove(m)
        # Cria os VAZMINT
        # - O primeiro é válido para os 2 primeiros meses
        newVazminT = VAZMINT()
        newVazminT.data_inicio = datetime(
            dger.ano_inicio_estudo, dger.mes_inicio_estudo, 1
        )
        newVazminT.vazao = rule.minLimit
        Log.log().info(
            f"Criando VAZMINT = {dger.mes_inicio_estudo}"
            + f" {dger.ano_inicio_estudo} {rule.minLimit}"
        )
        modif.data.add_after(usina, newVazminT)
        # - O segundo é para retornar ao valor anterior
        endDate = datetime(
            year=dger.ano_inicio_estudo, month=dger.mes_inicio_estudo, day=1
        ) + relativedelta(months=+2)
        nextVazminT = VAZMINT()
        nextVazminT.data_inicio = datetime(endDate.year, endDate.month, 1)
        nextVazminT.vazao = lastFlow
        Log.log().info(
            f"Criando VAZMINT = {endDate.month}"
            + f" {endDate.year} {lastFlow}"
        )
        modif.data.add_after(newVazminT, nextVazminT)
        return HTTPResponse(code=200, detail="success")

    def apply_qdef_qtur_max_re_rule(
        self,
        rule: ReservoirGroupRule,
        re: Re,
        hidr: pd.DataFrame,
        dger: Dger,
        code: int = None,
    ):
        if code is None:
            code = rule.uheCode
        # Se não existe um conjunto com a usina em questão, cria.
        setDfs = re.usinas_conjuntos
        sets = list(setDfs["conjunto"].unique())
        if code not in setDfs["codigo_usina"].to_numpy():
            Log.log().info(f"Criando conjunto com usina {code}")
            setNumber = max(sets) + 1
            re.usinas_conjuntos.loc[re.usinas_conjuntos.shape[0], :] = [
                setNumber,
                code,
            ]
            setDfs = re.usinas_conjuntos
        # Senão, identifica.
        setNumber = setDfs.loc[
            setDfs["codigo_usina"] == code, "conjunto"
        ].iloc[0]
        # Cria as restrições para o conjunto em questão, nos 2 primeiros
        # meses do horizonte
        startDate = datetime(
            year=dger.ano_inicio_estudo, month=dger.mes_inicio_estudo, day=1
        )
        endDate = startDate + relativedelta(months=+1)
        # Deleta as restrições do conjunto em questão, se existirem e começarem
        # em algum dos 2 primeiros meses
        constraints = re.restricoes
        constraintsIndices = constraints.loc[
            (constraints["conjunto"] == setNumber)
            & (
                (constraints["mes_inicio"] == startDate.month)
                | (constraints["mes_inicio"] == endDate.month)
            )
            & (
                (constraints["ano_inicio"] == startDate.year)
                | (constraints["ano_inicio"] == endDate.year)
            ),
            :,
        ].index
        constraints = constraints.drop(index=constraintsIndices)

        # Se a regra não tem limite máximo, ignora
        q_max = rule.maxLimit
        if q_max is None:
            return HTTPResponse(code=200, detail="ignored")

        re.restricoes.loc[re.restricoes.shape[0], :] = [
            setNumber,
            startDate.month,
            startDate.year,
            endDate.month,
            endDate.year,
            0,
            self.obtem_ghmax_usina(code, q_max, hidr),
            "REGRA ANA",
        ]
        return HTTPResponse(code=200, detail="success")

    def apply_qdef_rule(
        self,
        rule: ReservoirRule,
        hidr: pd.DataFrame,
        modif: Modif,
        re: Re,
        confhd: Confhd,
        dger: Dger,
    ) -> HTTPResponse:
        Log.log().info(f"Aplicando regra: {str(rule)}")
        # No caso de existirem, aplica também nas fictícias
        # Aplica a restrição da defluência mínima, se houver,
        # no modif.dat
        modifMap = NEWAVEReservoirRuleRepository.MAPA_FICTICIAS_MODIF
        if rule.minLimit is not None:
            if rule.uheCode in modifMap.keys():
                for code in modifMap[rule.uheCode]:
                    res = self.apply_qdef_modif_rule(
                        rule, modif, hidr, confhd, dger, code=code
                    )
                    if res.code != 200:
                        return res
            else:
                res = self.apply_qdef_modif_rule(
                    rule, modif, hidr, confhd, dger
                )
                if res.code != 200:
                    return res
        # Aplica a restrição da defluência máxima, se houver,
        # no re.dat
        mapa_re = NEWAVEReservoirRuleRepository.MAPA_FICTICIAS_RE
        if rule.maxLimit is not None:
            for code in mapa_re.get(rule.uheCode, [rule.uheCode]):
                res = self.apply_qdef_qtur_max_re_rule(
                    rule, re, hidr, dger, code=code
                )
                if res.code != 200:
                    return res
        return HTTPResponse(code=200, detail="success")

    def apply_qtur_min_modif_rule(
        self,
        rule: ReservoirGroupRule,
        modif: Modif,
        hidr: pd.DataFrame,
        confhd: Confhd,
        dger: Dger,
        code: int = None,
    ):
        if code is None:
            code = rule.uheCode
        # Se a regra não tem limite mínimo, ignora
        if rule.minLimit is None:
            return HTTPResponse(code=200, detail="ignored")

        modifUhe = modif.modificacoes_usina(code)
        # Se a usina em questão não é modificada, cria uma modificação nova
        if modifUhe is None:
            newUhe = USINA()
            newUhe.codigo = code
            newUhe.nome = str(hidr.at[code, "nome_usina"])
            modif.data.append(newUhe)
            Log.log().info(f"Criando novo registro USINA {code}")
            confhd.usinas.loc[
                confhd.usinas["codigo_usina"] == code, "usina_modificada"
            ] = 1
            Log.log().info(f"Modificando usina {code} no confhd.dat")
        # Obtém o registro que modifica a usina
        usina: USINA = modif.usina(codigo=code)

        actualTurbminT = [m for m in modifUhe if isinstance(m, TURBMINT)]
        Log.log().info(
            f"Existem {len(actualTurbminT)} TURBMINT" + f" para a usina {code}"
        )
        # Guarda a vazão do primeiro TURBMINT que tenha início após os
        # 2 primeiros meses. Se não existir, assume valor 0.0

        caseDate = datetime(
            year=dger.ano_inicio_estudo, month=dger.mes_inicio_estudo, day=1
        )
        lastFlow = 0.0
        if len(actualTurbminT) > 0:
            for m in actualTurbminT:
                lastFlow = m.turbinamento
                startDate = m.data_inicio
                if startDate >= caseDate + relativedelta(months=+2):
                    break
        Log.log().info(f"Último turbinamento = {lastFlow}")
        for m in actualTurbminT:
            # Deleta os TURBMINT que iniciem nos 2 primeiros meses
            startDate = m.data_inicio
            if startDate < caseDate + relativedelta(months=+2):
                modif.data.remove(m)
        # Cria os TURBMINT
        # - O primeiro é válido para os 2 primeiros meses
        newTurbminT = TURBMINT()
        newTurbminT.data_inicio = datetime(
            dger.ano_inicio_estudo, dger.mes_inicio_estudo, 1
        )
        newTurbminT.turbinamento = rule.minLimit
        Log.log().info(
            f"Criando TURBMINT = {dger.mes_inicio_estudo}"
            + f" {dger.ano_inicio_estudo} {rule.minLimit}"
        )
        modif.data.add_after(usina, newTurbminT)
        # - O segundo é para retornar ao valor anterior
        endDate = datetime(
            year=dger.ano_inicio_estudo, month=dger.mes_inicio_estudo, day=1
        ) + relativedelta(months=+2)
        nextTurbminT = TURBMINT()
        nextTurbminT.data_inicio = datetime(endDate.year, endDate.month, 1)
        nextTurbminT.turbinamento = lastFlow
        Log.log().info(
            f"Criando TURBMINT = {endDate.month}"
            + f" {endDate.year} {lastFlow}"
        )
        modif.data.add_after(newTurbminT, nextTurbminT)
        return HTTPResponse(code=200, detail="success")

    def apply_qtur_max_modif_rule(
        self,
        rule: ReservoirGroupRule,
        modif: Modif,
        hidr: pd.DataFrame,
        confhd: Confhd,
        dger: Dger,
        code: int = None,
    ):
        if code is None:
            code = rule.uheCode
        # Se a regra não tem limite máximo, ignora
        if rule.maxLimit is None:
            return HTTPResponse(code=200, detail="ignored")

        modifUhe = modif.modificacoes_usina(code)
        # Se a usina em questão não é modificada, cria uma modificação nova
        if modifUhe is None:
            newUhe = USINA()
            newUhe.codigo = code
            newUhe.nome = str(hidr.at[code, "nome_usina"])
            modif.data.append(newUhe)
            Log.log().info(f"Criando novo registro USINA {code}")
            confhd.usinas.loc[
                confhd.usinas["codigo_usina"] == code, "usina_modificada"
            ] = 1
            Log.log().info(f"Modificando usina {code} no confhd.dat")
        # Obtém o registro que modifica a usina
        usina: USINA = modif.usina(codigo=code)

        actualTurbmaxT = [m for m in modifUhe if isinstance(m, TURBMAXT)]
        Log.log().info(
            f"Existem {len(actualTurbmaxT)} TURBMAXT" + f" para a usina {code}"
        )
        # Guarda a vazão do primeiro TURBMAXT que tenha início após os
        # 2 primeiros meses. Se não existir, assume valor do engolimento
        # da usina.

        caseDate = datetime(
            year=dger.ano_inicio_estudo, month=dger.mes_inicio_estudo, day=1
        )
        lastFlow = self.obtem_engolimento_usina(code, hidr)
        if len(actualTurbmaxT) > 0:
            for m in actualTurbmaxT:
                lastFlow = m.turbinamento
                startDate = m.data_inicio
                if startDate >= caseDate + relativedelta(months=+2):
                    break
        Log.log().info(f"Último turbinamento = {lastFlow}")
        for m in actualTurbmaxT:
            # Deleta os TURBMAXT que iniciem nos 2 primeiros meses
            startDate = m.data_inicio
            if startDate < caseDate + relativedelta(months=+2):
                modif.data.remove(m)
        # Cria os TURBMAXT
        # - O primeiro é válido para os 2 primeiros meses
        newTurbmaxT = TURBMAXT()
        newTurbmaxT.data_inicio = datetime(
            dger.ano_inicio_estudo, dger.mes_inicio_estudo, 1
        )
        newTurbmaxT.turbinamento = min(
            [rule.maxLimit, self.obtem_engolimento_usina(code, hidr)]
        )
        Log.log().info(
            f"Criando TURBMAXT = {dger.mes_inicio_estudo}"
            + f" {dger.ano_inicio_estudo} {rule.maxLimit}"
        )
        modif.data.add_after(usina, newTurbmaxT)
        # - O segundo é para retornar ao valor anterior
        endDate = datetime(
            year=dger.ano_inicio_estudo, month=dger.mes_inicio_estudo, day=1
        ) + relativedelta(months=+2)
        nextTurbmaxT = TURBMAXT()
        nextTurbmaxT.data_inicio = datetime(endDate.year, endDate.month, 1)
        nextTurbmaxT.turbinamento = lastFlow
        Log.log().info(
            f"Criando TURBMINT = {endDate.month}"
            + f" {endDate.year} {lastFlow}"
        )
        modif.data.add_after(newTurbmaxT, nextTurbmaxT)
        return HTTPResponse(code=200, detail="success")

    def apply_qtur_rule(
        self,
        rule: ReservoirRule,
        hidr: pd.DataFrame,
        modif: Modif,
        re: Re,
        confhd: Confhd,
        dger: Dger,
    ) -> HTTPResponse:
        Log.log().info(f"Aplicando regra: {str(rule)}")
        # No caso de existirem, aplica também nas fictícias
        # Aplica a restrição de turbinamento mínimo, se houver,
        # no modif.dat
        modifMap = NEWAVEReservoirRuleRepository.MAPA_FICTICIAS_MODIF
        if rule.minLimit is not None:
            for code in modifMap.get(rule.uheCode, [rule.uheCode]):
                res = self.apply_qtur_min_modif_rule(
                    rule, modif, hidr, confhd, dger, code=code
                )
                if res.code != 200:
                    return res

        # Aplica a restrição de turbinamento máximo, se houver,
        # no modif.dat
        if rule.maxLimit is not None:
            for code in modifMap.get(rule.uheCode, [rule.uheCode]):
                res = self.apply_qtur_max_modif_rule(
                    rule, modif, hidr, confhd, dger, code=code
                )
                if res.code != 200:
                    return res
                res = self.apply_qdef_qtur_max_re_rule(
                    rule, re, hidr, dger, code
                )
                if res.code != 200:
                    return res

        return HTTPResponse(code=200, detail="success")

    def apply_rule(
        self,
        rule: ReservoirRule,
        hidr: pd.DataFrame,
        modif: Modif,
        re: Re,
        confhd: Confhd,
        dger: Dger,
    ) -> HTTPResponse:
        rule_handler_map: Dict[str, Callable] = {
            "QDEF": self.apply_qdef_rule,
            "QTUR": self.apply_qtur_rule,
        }
        handler = rule_handler_map[rule.constraintType]
        return handler(rule, hidr, modif, re, confhd, dger)

    async def apply(
        self,
        rules: List[ReservoirRule],
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ReservoirGroupRule], HTTPResponse]:
        # Obtém o último DECOMP executado no mês anterior
        with destination_uow:
            dger = await destination_uow.files.get_dger()
        if isinstance(dger, HTTPResponse):
            return dger

        right_source_uow = None
        newaveMonth = dger.mes_inicio_estudo
        previousMonth = 12 if newaveMonth == 11 else newaveMonth - 1
        for s in reversed(sources_uow):
            with s:
                dadger = await s.files.get_dadger()
                if isinstance(dadger, HTTPResponse):
                    return dadger
                # PREMISSA: a data do registro DT + 6 dias sempre
                # tem o mês do caso.
                decompDate = datetime(
                    year=dadger.dt.ano,
                    month=dadger.dt.mes,
                    day=dadger.dt.dia,
                )
                decompActualMonth = (decompDate + timedelta(days=6)).month
                if decompActualMonth == previousMonth:
                    right_source_uow = s

        if right_source_uow is None:
            msg = (
                "Caso não possui DECOMP anterior. "
                + "Não serão aplicadas regras operativas de reservatórios."
            )
            Log.log().info(msg)
            return HTTPResponse(code=404, detail=msg)

        with right_source_uow:
            relato = right_source_uow.files.get_relato()
        if isinstance(relato, HTTPResponse):
            return relato

        # Filtra as regras de operação para o mês do caso
        regras_mes = self.regras_mes(rules, newaveMonth)

        with destination_uow:
            hidr = destination_uow.files.get_hidr()
        if isinstance(hidr, HTTPResponse):
            return hidr
        cadastro_hidr = hidr.cadastro

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
        regras_ativas = self.identify_active_rules(
            regras_agrupadas, volumes_relato_hm3
        )

        # Para o NEWAVE, são sempre tomadas as regras vigentes para os
        # volumes do últimos estágio semanal do último DECOMP do mês anterior
        estagio = sorted(list(regras_ativas.keys()))[-1]
        appliedRules: List[ReservoirGroupRule] = []
        with destination_uow:
            modif = destination_uow.files.get_modif()
            re = destination_uow.files.get_re()
            confhd = destination_uow.files.get_confhd()
        if isinstance(modif, HTTPResponse):
            return modif
        if isinstance(re, HTTPResponse):
            return re
        if isinstance(confhd, HTTPResponse):
            return confhd
        for r in regras_ativas[estagio]:
            res = self.apply_rule(r, cadastro_hidr, modif, re, confhd, dger)
            if res.code != 200:
                return res
            else:
                appliedRules.append(
                    self.converte_regra_equiv_percent(r, cadastro_hidr)
                )
        with destination_uow:
            res = destination_uow.files.set_modif(modif)
            if res.code != 200:
                return res
            res = destination_uow.files.set_re(re)
            if res.code != 200:
                return res
            res = destination_uow.files.set_confhd(confhd)
            if res.code != 200:
                return res
        return appliedRules


class DECOMPReservoirRuleRepository(AbstractReservoirRuleRepository):
    """ """

    # Override
    def identifica_regra_ativa(
        self,
        rules: List[ReservoirGroupRule],
        uheCode: int,
        volumes: pd.DataFrame,
        estagio: int,
    ) -> Optional[ReservoirGroupRule]:
        reservoirCodes = next(
            r.reservoirCodes for r in rules if r.uheCode == uheCode
        )
        totalVolume = float(
            volumes.loc[
                volumes["codigo_usina"].isin(reservoirCodes),
                f"estagio_{estagio}",
            ].sum()
        )
        try:
            rule = None
            for r in rules:
                if all(
                    [
                        r.uheCode == uheCode,
                        r.minVolume <= totalVolume < r.maxVolume,
                    ]
                ):
                    rule = r
                    break
            if rule is None:
                raise StopIteration()
        except StopIteration:
            Log.log().warning(
                "Não foi encontrada regra de operação ativa "
                + f"para a usina {uheCode} "
                + f"(reservatórios {reservoirCodes}) "
                + f"no volume {totalVolume}"
            )
            rule = None
        return rule

    def identifica_regras_ativas(
        self,
        rules: Dict[int, List[ReservoirGroupRule]],
        uheVolumesHm3: pd.DataFrame,
    ) -> Dict[int, List[ReservoirGroupRule]]:
        activeRulesByStage: Dict[int, List[ReservoirGroupRule]] = {}
        # Obtém as regras ativas para cada usina
        for stage, rulesInStage in rules.items():
            uhesWithRules = list(set([r.uheCode for r in rulesInStage]))
            activeRules: List[ReservoirGroupRule] = []
            for u in uhesWithRules:
                stageRule = self.identifica_regra_ativa(
                    rules[stage], u, uheVolumesHm3, stage
                )
                if stageRule is not None:
                    activeRules.append(stageRule)
            activeRulesByStage[stage] = activeRules
        return activeRulesByStage

    def aplica_regra_qdef_qtur(
        self, rule: ReservoirGroupRule, dadger: Dadger, estagio: int
    ):
        # Se vai aplicar uma regra em um determinado estágio
        # acessa a restrição em todos os estágios futuros, até
        # o limite, para garantir que os valores serão mantidos.
        cqs: List[CQ] = dadger.cq()
        if isinstance(cqs, CQ):
            cqs = [cqs]
        if isinstance(cqs, list):
            cqs_usina = [
                c
                for c in cqs
                if (
                    (c.codigo_usina == rule.uheCode)
                    and (c.tipo == rule.constraintType)
                )
            ]
            # TODO - Não está tratanto restrições conjuntas.
            # Para todos os CQs encontrados para a usina, filtra por código de HQ
            # e elimina as HQs com mais de um CQ.
            if len(cqs_usina) > 0:
                codigos_restricoes = [cq.codigo_restricao for cq in cqs_usina]
            else:
                codigo_nova_restricao = cqs[-1].codigo_restricao + 1
                codigos_restricoes = [codigo_nova_restricao]
                estagio_final = len(dadger.dp(codigo_submercado=1))

                hq_novo = HQ()
                hq_novo.codigo_restricao = codigo_nova_restricao
                hq_novo.estagio_inicial = 1
                hq_novo.estagio_final = estagio_final
                dadger.data.add_after(cqs[-1], hq_novo)

                lq_novo = LQ()
                lq_novo.codigo_restricao = codigo_nova_restricao
                lq_novo.estagio = 1
                dadger.data.add_after(hq_novo, lq_novo)

                cq_novo = CQ()
                cq_novo.codigo_restricao = codigo_nova_restricao
                cq_novo.estagio = 1
                cq_novo.codigo_usina = rule.uheCode
                cq_novo.coeficiente = 1
                cq_novo.tipo = rule.constraintType
                dadger.data.add_after(lq_novo, cq_novo)
            efs = [
                dadger.hq(codigo_restricao=codigo).estagio_final
                for codigo in codigos_restricoes
            ]

        for codigo, ef in zip(codigos_restricoes, efs):
            for e in range(estagio, ef + 1):
                dadger.lq(codigo, e)
            # Aplica a regra no estágio devido, se tiver limites inf/sup
            if rule.minLimit is not None:
                dadger.lq(codigo, estagio).limite_inferior = [
                    rule.minLimit
                ] * 3
            if rule.maxLimit is not None:
                dadger.lq(codigo, estagio).limite_superior = [
                    rule.maxLimit
                ] * 3

    def aplica_regra(
        self,
        dadger: Dadger,
        rule: ReservoirGroupRule,
        applicationStage: int,
    ) -> HTTPResponse:
        Log.log().info(
            f"Aplicando regra: {str(rule)} no estágio {applicationStage}"
        )
        # Se ocorrer algum erro, retorna False
        if rule.constraintType in ["QDEF", "QTUR"]:
            self.aplica_regra_qdef_qtur(rule, dadger, applicationStage)
        else:
            return HTTPResponse(
                code=500, detail=f"error applying rule {str(rule)}"
            )
        return HTTPResponse(code=200, detail="success")

    def mapeia_semanas_dias_fim(
        self, dadger: Dadger, relato: Relato, delta_inicial: int = 0
    ) -> Dict[int, datetime]:
        dt = dadger.dt
        dia_inicio_caso_atual = datetime(year=dt.ano, month=dt.mes, day=dt.dia)
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
        rules: List[ReservoirRule],
        stageDayMap: Dict[int, datetime],
    ) -> Dict[int, List[ReservoirRule]]:
        mappedRules: Dict[int, List[ReservoirRule]] = {}
        for stage, endDate in stageDayMap.items():
            mappedRules[stage] = list(
                set([r for r in rules if r.month == endDate.month])
            )
        return mappedRules

    def aplica_regras_caso(
        self,
        rules: List[ReservoirRule],
        dadger: Dadger,
        relato: Relato,
        hidr: pd.DataFrame,
        weekGap: int = 0,
        monthly: bool = False,
    ) -> Union[List[ReservoirGroupRule], HTTPResponse]:
        # Identifica o dia de fim de cada semana do DECOMP anterior
        endDayMaps = self.mapeia_semanas_dias_fim(dadger, relato, weekGap)
        # Se está falando de regras mensais, não consulta semana a semana
        if monthly:
            decompDate = datetime(
                year=dadger.dt.ano,
                month=dadger.dt.mes,
                day=dadger.dt.dia,
            )
            decompActualDate = decompDate + timedelta(days=6)
            endDayMaps = {
                1: datetime(
                    year=decompActualDate.year,
                    month=decompActualDate.month,
                    day=1,
                )
            }
        Log.log().info(
            f"Dias de fim dos estágios do DECOMP anterior: {endDayMaps}"
        )

        # Filtra as regras de operação para cada estágio
        # do DECOMP anterior
        stageRules = self.regras_estagios(rules, endDayMaps)

        # Converte as regras para hm3
        rulesHm3: Dict[int, List[ReservoirRule]] = {
            e: [self.converte_regra_hm3(r, hidr) for r in rules]
            for e, rules in stageRules.items()
        }

        # Agrupa regras por usina com defluência limitada
        regras_agrupadas: Dict[int, List[ReservoirGroupRule]] = {
            e: self.agrupa_usinas_defluencia(regras)
            for e, regras in rulesHm3.items()
        }

        volumes_relato_hm3 = self.converte_volumes_relato_hm3(
            relato.volume_util_reservatorios, hidr
        )

        # Identifica as regras ativas
        activeRules = self.identifica_regras_ativas(
            regras_agrupadas, volumes_relato_hm3
        )

        # Aplica as regras ativas
        DPregisters = dadger.dp()
        subsystemCount = len(dadger.sb())
        num_estagios = int(len(DPregisters) / subsystemCount)
        currentDecompStages = list(range(1, num_estagios + 1))
        appliedRules: List[ReservoirGroupRule] = []
        for estagio in currentDecompStages:
            Log.log().info(
                f"Aplicando regras de reservatórios no estágio {estagio}"
            )
            if estagio not in activeRules.keys():
                applicationStage = sorted(list(activeRules.keys()))[-1]
            else:
                applicationStage = estagio
            for r in activeRules[applicationStage]:
                res = self.aplica_regra(dadger, r, estagio)
                if res.code != 200:
                    return res
                else:
                    appliedRules.append(
                        self.converte_regra_equiv_percent(r, hidr)
                    )

        return appliedRules

    async def apply(
        self,
        rules: List[ReservoirRule],
        sources_uow: List[AbstractUnitOfWork],
        destination_uow: AbstractUnitOfWork,
    ) -> Union[List[ReservoirGroupRule], HTTPResponse]:
        allResults: List[ReservoirGroupRule] = []
        # Obtém o último DECOMP executado
        with destination_uow:
            currentDadger = await destination_uow.files.get_dadger()
        if isinstance(currentDadger, HTTPResponse):
            return currentDadger

        weeklyRules = list(set([r for r in rules if r.frequency == "S"]))
        decompSources = [s for s in sources_uow if s.program == Program.DECOMP]
        if len(decompSources) == 0:
            msg = (
                "Caso não possui DECOMP anterior. "
                + "Não serão aplicadas regras operativas de reservatórios "
                + "com periodicidade semanal."
            )
            Log.log().info(msg)
        else:
            lastDecompSource = decompSources[-1]
            with lastDecompSource:
                relato = lastDecompSource.files.get_relato()
                hidr = lastDecompSource.files.get_hidr()
            if isinstance(relato, HTTPResponse):
                return relato
            if isinstance(hidr, HTTPResponse):
                return hidr

            Log.log().info("Aplicando regras SEMANAIS")
            weeklyResult = self.aplica_regras_caso(
                weeklyRules, currentDadger, relato, hidr.cadastro
            )
            if isinstance(weeklyResult, HTTPResponse):
                if weeklyResult.code != 404:
                    return weeklyResult
            else:
                allResults += weeklyResult

        currentDecompDate = datetime(
            year=currentDadger.dt.ano,
            month=currentDadger.dt.mes,
            day=currentDadger.dt.dia,
        )
        currentDecompActualMonth = (
            currentDecompDate + timedelta(days=6)
        ).month
        previousMonth = (
            12
            if currentDecompActualMonth == 11
            else currentDecompActualMonth - 1
        )
        right_source_uow = None
        for s in reversed(decompSources):
            with s:
                dadger = await s.files.get_dadger()
                if isinstance(dadger, HTTPResponse):
                    return dadger
                # PREMISSA: a data do registro DT + 6 dias sempre
                # tem o mês do caso.
                decompDate = datetime(
                    year=dadger.dt.ano,
                    month=dadger.dt.mes,
                    day=dadger.dt.dia,
                )
                decompActualMonth = (decompDate + timedelta(days=6)).month
                if decompActualMonth == previousMonth:
                    right_source_uow = s

        if right_source_uow is None:
            msg = (
                "Caso não possui DECOMP anterior. "
                + "Não serão aplicadas regras operativas de reservatórios "
                + "com periodicidade mensal."
            )
            Log.log().info(msg)
        else:
            monthlyRules = list(set([r for r in rules if r.frequency == "M"]))
            weekGap = (
                len(sources_uow) - sources_uow.index(right_source_uow) - 2
            )

            with right_source_uow:
                relato = right_source_uow.files.get_relato()
            if isinstance(relato, HTTPResponse):
                return relato

            Log.log().info("Aplicando regras MENSAIS")
            monthlyResult = self.aplica_regras_caso(
                monthlyRules,
                currentDadger,
                relato,
                hidr.cadastro,
                weekGap,
                True,
            )
            if isinstance(monthlyResult, HTTPResponse):
                if monthlyResult.code != 404:
                    return monthlyResult
            else:
                allResults += monthlyResult

        with destination_uow:
            destination_uow.files.set_dadger(currentDadger)

        return allResults


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
