"""Schemas de saída da página Analytics.

Os quatro primeiros campos repetem os da AnalyticsPage do front-end: na
integração, o front só troca o cálculo local pela chamada à API. Os três
últimos são análises novas, e podem vir null quando não há dados.
"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from app.models.enums import PrioridadeTarefa
from app.schemas.base import EsquemaDeSaida


class ConcluidasNoDia(EsquemaDeSaida):
    dia: date
    quantidade: int


class AnalyticsOut(EsquemaDeSaida):
    total: int
    concluidas: int
    taxa_conclusao: int = Field(
        description="Percentual de tarefas concluídas (0–100), arredondado"
    )
    concluidas_na_janela: int = Field(
        description="Total de conclusões dentro da janela de dias consultada"
    )
    concluidas_por_dia: list[ConcluidasNoDia]
    pendentes_por_prioridade: dict[PrioridadeTarefa, int]
    # Campos novos — podem ser null quando não há dados
    tempo_medio_conclusao_dias: float | None = Field(
        description="Média de dias entre criação e conclusão; null se nenhuma concluída"
    )
    concluidas_por_dia_da_semana: dict[str, int] = Field(
        description="Contagem histórica de conclusões por dia da semana (seg…dom)"
    )
    percentual_no_prazo: int | None = Field(
        description=(
            "% das concluídas com prazo que foram entregues no prazo; "
            "null se nenhuma concluída tinha prazo"
        )
    )