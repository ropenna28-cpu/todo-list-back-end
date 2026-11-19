"""Acesso aos dados de tarefa: filtros, ordenação e paginação."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import case

from app.models import Tarefa
from app.models.enums import CampoOrdenacao, Ordem, PrioridadeTarefa, StatusTarefa
from app.repositories.base import RepositorioBase


@dataclass(frozen=True)
class FiltroDeTarefas:
    """Critérios de uma consulta de tarefas.

    Existe para que a assinatura de `TarefaRepositorio.listar` não cresça até
    oito parâmetros posicionais, e para que acrescentar um filtro novo não
    mude a assinatura de quem já a chama.
    """

    usuario_id: int
    status: StatusTarefa | None = None
    prioridade: PrioridadeTarefa | None = None
    prazo_ate: date | None = None
    busca: str | None = None
    ordenar_por: CampoOrdenacao = CampoOrdenacao.CRIADO_EM
    ordem: Ordem = Ordem.DESC
    limite: int = 100
    deslocamento: int = 0


@dataclass(frozen=True)
class PaginaDeTarefas:
    """Uma página da listagem e o total de tarefas que atendem ao filtro.

    O total existe porque uma lista sozinha não diz se há mais tarefas: com
    100 por página e 250 tarefas, o cliente precisa saber que o total é 250.
    """

    tarefas: list[Tarefa]
    total: int


class TarefaRepositorio(RepositorioBase[Tarefa]):
    """Acesso aos dados de tarefa."""

    # Ordena pela prioridade seguindo os pesos (urgente, alta, média, baixa),
    # e não pela ordem alfabética do texto.
    _ORDEM_POR_PRIORIDADE = case(
        PrioridadeTarefa.mapa_de_pesos(), value=Tarefa.prioridade, else_=99
    )

    @property
    def modelo(self) -> type[Tarefa]:
        return Tarefa

    def _coluna_de_ordenacao(self, campo: CampoOrdenacao):
        """Devolve a expressão SQL correspondente ao campo de ordenação."""
        colunas = {
            CampoOrdenacao.CRIADO_EM: Tarefa.criado_em,
            CampoOrdenacao.PRAZO: Tarefa.prazo,
            CampoOrdenacao.PRIORIDADE: self._ORDEM_POR_PRIORIDADE,
        }
        return colunas[campo]

    def listar(self, filtro: FiltroDeTarefas) -> PaginaDeTarefas:
        """Lista as tarefas de um usuário conforme os critérios informados.

        Os filtros são encadeados: cada critério preenchido acrescenta uma
        condição ao WHERE. Devolve uma página, com o total de tarefas que
        atendem ao filtro (antes de cortar a página).
        """
        consulta = self.sessao.query(Tarefa).filter(
            Tarefa.usuario_id == filtro.usuario_id
        )
        if filtro.status is not None:
            consulta = consulta.filter(Tarefa.status == filtro.status.value)
        if filtro.prioridade is not None:
            consulta = consulta.filter(
                Tarefa.prioridade == filtro.prioridade.value
            )
        if filtro.prazo_ate is not None:
            consulta = consulta.filter(
                Tarefa.prazo.isnot(None), Tarefa.prazo <= filtro.prazo_ate
            )
        if filtro.busca:
            # icontains = "contém", sem diferenciar maiúsculas. O autoescape
            # faz % e _ serem procurados como texto, e não como curingas do LIKE.
            consulta = consulta.filter(
                Tarefa.titulo.icontains(filtro.busca, autoescape=True)
            )

        # O total é contado ANTES de aplicar limite e deslocamento.
        total = consulta.order_by(None).count()

        coluna = self._coluna_de_ordenacao(filtro.ordenar_por)
        ordenacao = [coluna.desc() if filtro.ordem is Ordem.DESC else coluna.asc()]
        if filtro.ordenar_por is CampoOrdenacao.PRAZO:
            # Tarefa sem prazo vai sempre para o FIM, em qualquer sentido. Cada
            # banco põe o NULL num lugar diferente; este critério vem antes e
            # resolve igual em todos: 0 = tem prazo, 1 = sem prazo.
            ordenacao.insert(0, case((Tarefa.prazo.is_(None), 1), else_=0))
        # Desempate pelo id: sem ele, tarefas com o mesmo valor (ex.: mesma
        # prioridade) poderiam trocar de lugar entre uma página e outra.
        ordenacao.append(Tarefa.id.desc())

        tarefas = (
            consulta.order_by(*ordenacao)
            .offset(filtro.deslocamento)
            .limit(filtro.limite)
            .all()
        )
        return PaginaDeTarefas(tarefas=tarefas, total=total)

    def todas_do_usuario(self, usuario_id: int) -> list[Tarefa]:
        """Todas as tarefas de um usuário, sem filtro nem limite (para o resumo)."""
        return self.sessao.query(Tarefa).filter(Tarefa.usuario_id == usuario_id).all()
