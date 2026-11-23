"""Análise das tarefas do usuário para a página Analytics.

Ideia central: transformar a lista de tarefas num DataFrame (uma linha por
tarefa) e responder perguntas sobre a tabela inteira de uma vez, sem for.

As quatro primeiras métricas são as da página do front-end (taxa de conclusão,
concluídas por dia, pendentes por prioridade e total). As três últimas são
análises novas: tempo médio para concluir, conclusões por dia da semana e
percentual concluído no prazo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd

from app.models.enums import PrioridadeTarefa, StatusTarefa
from app.repositories import TarefaRepositorio
from app.models import Tarefa

# No pandas, 0 = segunda-feira, 6 = domingo
DIAS_DA_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]


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
    # Análises novas — podem ser None quando não há dados suficientes
    tempo_medio_conclusao_dias: float | None
    concluidas_por_dia_da_semana: dict[str, int]
    percentual_no_prazo: int | None


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
            # Análises novas
            tempo_medio_conclusao_dias=self._tempo_medio_conclusao(concluidas),
            concluidas_por_dia_da_semana=self._por_dia_da_semana(concluidas),
            percentual_no_prazo=self._percentual_no_prazo(concluidas),
        )

    # --- a tabela -----------------------------------------------------------

    @staticmethod
    def _montar_tabela(tarefas: list[Tarefa]) -> pd.DataFrame:
        """Converte a lista de tarefas num DataFrame (uma linha por tarefa).

        `StatusTarefa(...)` e `PrioridadeTarefa(...)` aceitam tanto o enum quanto
        o texto ("baixa"), e `.value` devolve sempre o texto.
        """
        fuso_do_servidor = datetime.now().astimezone().tzinfo

        tabela = pd.DataFrame({
            "status":      [StatusTarefa(t.status).value for t in tarefas],
            "prioridade":  [PrioridadeTarefa(t.prioridade).value for t in tarefas],
            "concluido_em": [t.concluido_em for t in tarefas],
            "criado_em":   [t.criado_em for t in tarefas],
            "prazo":       [t.prazo for t in tarefas],
        })

        # Aplica a mesma conversão de fuso às duas colunas de instantes.
        # utc=True: o SQLite devolve datas sem fuso; como a aplicação sempre
        # grava em UTC, lemos sem fuso como UTC.
        # A criado_em passa pelo mesmo fuso para que a subtração concluido_em - criado_em
        # compare horários do mesmo fuso.
        for coluna in ("criado_em", "concluido_em"):
            tabela[coluna] = (
                pd.to_datetime(tabela[coluna], utc=True)
                .dt.tz_convert(fuso_do_servidor)
            )

        # O prazo NÃO passa pela conversão: é uma data (sem hora), não um instante.
        # .dt.date fica só com o dia (sem hora) — para agrupar por dia.
        # Tarefa pendente não tem data de conclusão: vira NaT na coluna.
        tabela["dia_conclusao"] = tabela["concluido_em"].dt.date

        return tabela

    # --- as métricas que o front já usa -------------------------------------

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

    # --- análises novas (pandas) --------------------------------------------

    @staticmethod
    def _tempo_medio_conclusao(concluidas: pd.DataFrame) -> float | None:
        """Média de dias entre a criação e a conclusão de cada tarefa.

        Subtrai as duas colunas de datas diretamente — o pandas devolve uma
        coluna de durações, uma por tarefa, sem precisar de for.
        Devolve None se não há nada concluído.
        """
        if concluidas.empty:
            return None

        duracao = concluidas["concluido_em"] - concluidas["criado_em"]
        return round(float((duracao.dt.total_seconds() / 86400).mean()), 1)

    @staticmethod
    def _por_dia_da_semana(concluidas: pd.DataFrame) -> dict[str, int]:
        """Quantas tarefas foram concluídas em cada dia da semana (histórico inteiro)."""
        contagem = (
            concluidas["concluido_em"]
            .dt.dayofweek
            .value_counts()
            .reindex(range(7), fill_value=0)
        )

        return {DIAS_DA_SEMANA[numero]: int(qtd) for numero, qtd in contagem.items()}

    @staticmethod
    def _percentual_no_prazo(concluidas: pd.DataFrame) -> int | None:
        """Das concluídas com prazo, quantas % foram concluídas até o prazo.

        'No prazo' inclui o próprio dia do prazo (<=, não <).
        Devolve None se nenhuma concluída tinha prazo.
        """
        # notna(): só as que tinham prazo entram na conta
        com_prazo = concluidas[concluidas["prazo"].notna()]
        if com_prazo.empty:
            return None

        no_prazo = com_prazo["dia_conclusao"] <= com_prazo["prazo"]
        # média de True/False = proporção de True (True vale 1, False vale 0)
        return arredondar(no_prazo.mean() * 100)