"""Análise das tarefas do usuário para a página Analytics.

Ideia central: transformar a lista de tarefas num DataFrame (uma linha por
tarefa) e responder perguntas sobre a tabela inteira de uma vez, sem for.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd

from app.models.enums import PrioridadeTarefa, StatusTarefa
from app.repositories import TarefaRepositorio
from app.models import Tarefa


def arredondar(valor: float) -> int:
    """Arredonda seguindo a regra do JavaScript (Math.round): ,5 sobe sempre.

    O round() nativo do Python usa 'arredondamento bancário': 12,5 vira 12
    (par mais próximo). O Math.round do JS sobe: 12,5 vira 13. Para que
    servidor e front-end mostrem o mesmo número, usamos a mesma regra.
    """
    return math.floor(valor + 0.5)


@dataclass(frozen=True)
class Analytics:
    total: int
    concluidas: int
    taxa_conclusao: int
    concluidas_na_janela: int
    concluidas_por_dia: list[dict]
    pendentes_por_prioridade: dict[PrioridadeTarefa, int]


class AnalyticsServico:
    def __init__(self, tarefas: TarefaRepositorio) -> None:
        self._tarefas = tarefas

    def calcular(
        self,
        usuario_id: int,
        dias: int = 7,
        hoje: date | None = None,
    ) -> Analytics:
        hoje = hoje or date.today()
        tabela = self._montar_tabela(self._tarefas.todas_do_usuario(usuario_id))

        # Filtro booleano: devolve uma coluna de True/False, uma linha por tarefa
        concluida = tabela["status"] == StatusTarefa.CONCLUIDA.value
        concluidas = tabela[concluida]   # linhas onde status == concluída
        pendentes = tabela[~concluida]   # linhas onde status != concluída (~ inverte)

        total = len(tabela)
        por_dia = self._concluidas_por_dia(concluidas, dias, hoje)

        return Analytics(
            total=total,
            concluidas=len(concluidas),
            # if total else 0: evita divisão por zero para usuário sem tarefas
            taxa_conclusao=arredondar(len(concluidas) / total * 100) if total else 0,
            concluidas_na_janela=sum(item["quantidade"] for item in por_dia),
            concluidas_por_dia=por_dia,
            pendentes_por_prioridade=self._pendentes_por_prioridade(pendentes),
        )

    # --- a tabela -----------------------------------------------------------

    @staticmethod
    def _montar_tabela(tarefas: list[Tarefa]) -> pd.DataFrame:
        """Converte a lista de tarefas num DataFrame (uma linha por tarefa)."""
        fuso_do_servidor = datetime.now().astimezone().tzinfo

        tabela = pd.DataFrame({
            "status":      [t.status.value for t in tarefas],
            "prioridade":  [t.prioridade.value for t in tarefas],
            "concluido_em": [t.concluido_em for t in tarefas],
        })

        # utc=True: o SQLite devolve datas sem fuso; como a aplicação sempre
        # grava em UTC, lemos sem fuso como UTC.
        tabela["concluido_em"] = (
            pd.to_datetime(tabela["concluido_em"], utc=True)
            .dt.tz_convert(fuso_do_servidor)
        )

        # .dt.date fica só com o dia (sem hora) — para agrupar por dia.
        # Tarefa pendente não tem data: vira NaT na coluna.
        tabela["dia_conclusao"] = tabela["concluido_em"].dt.date

        return tabela

    # --- as métricas --------------------------------------------------------

    @staticmethod
    def _concluidas_por_dia(concluidas: pd.DataFrame, dias: int, hoje: date) -> list[dict]:
        # Janela: do dia mais antigo até hoje
        janela = [hoje - timedelta(days=n) for n in range(dias - 1, -1, -1)]

        # value_counts() conta quantas vezes cada dia aparece.
        # reindex() impõe a janela completa e preenche os dias ausentes com 0.
        contagem = (
            concluidas["dia_conclusao"]
            .value_counts()
            .reindex(janela, fill_value=0)
        )

        return [{"dia": dia, "quantidade": int(qtd)} for dia, qtd in contagem.items()]

    @staticmethod
    def _pendentes_por_prioridade(pendentes: pd.DataFrame) -> dict[PrioridadeTarefa, int]:
        # Ordem da mais urgente à menos urgente
        ordem = [p.value for p in sorted(PrioridadeTarefa, key=lambda p: p.peso)]

        contagem = (
            pendentes["prioridade"]
            .value_counts()
            .reindex(ordem, fill_value=0)
        )

        # int(): converte numpy.int64 para int nativo do Python
        return {PrioridadeTarefa(prioridade): int(qtd) for prioridade, qtd in contagem.items()}