"""Schemas de saída da página Analytics.

Os campos repetem os da AnalyticsPage do front-end: na integração,
o front só troca o cálculo local pela chamada à API.
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
    taxa_conclusao: int = Field(description="Percentual de tarefas concluídas (0–100), arredondado")
    concluidas_na_janela: int = Field(description="Total de conclusões dentro da janela de dias consultada")
    concluidas_por_dia: list[ConcluidasNoDia]
    pendentes_por_prioridade: dict[PrioridadeTarefa, int]