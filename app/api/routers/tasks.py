"""Endpoints de tarefas: todos exigem login.

O dono das tarefas é SEMPRE quem está autenticado (vem do token). Não existe
mais `usuarioId` na URL nem no corpo: antes, bastava trocar esse número para
ler, alterar ou apagar a tarefa de outra pessoa.

Os nomes públicos dos parâmetros ficam em camelCase (`prazoAte`) e, no Python,
em snake_case (`prazo_ate`) — o `alias` faz a ponte.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import UsuarioAtual, obter_tarefa_servico
from app.models.enums import PrioridadeTarefa, StatusTarefa
from app.repositories import FiltroDeTarefas
from app.schemas import TarefaCreate, TarefaOut, TarefaUpdate
from app.services import AlteracoesDaTarefa, TarefaServico

router = APIRouter(
    prefix="/tasks",
    tags=["Tarefas"],
    responses={401: {"description": "Sem token, ou token inválido/expirado"}},
)

Servico = Annotated[TarefaServico, Depends(obter_tarefa_servico)]

_RESPOSTAS_DE_UMA_TAREFA: dict[int | str, dict[str, str]] = {
    403: {"description": "A tarefa pertence a outro usuário"},
    404: {"description": "Tarefa não encontrada"},
}


def _montar_alteracoes(dados: TarefaUpdate) -> AlteracoesDaTarefa:
    """Converte o corpo do PATCH em alterações de domínio.

    `exclude_unset=True` é a outra metade da sentinela: sem ele, o
    `model_dump()` devolveria todos os campos, com None nos que não vieram —
    e o PATCH apagaria o que não foi mencionado.
    """
    return AlteracoesDaTarefa(**dados.model_dump(exclude_unset=True))


@router.post(
    "",
    response_model=TarefaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar tarefa",
)
def criar_task(dados: TarefaCreate, usuario: UsuarioAtual, servico: Servico) -> TarefaOut:
    """Cria uma tarefa para o usuário logado. Nasce sempre pendente."""
    return servico.criar(
        usuario_id=usuario.id,
        titulo=dados.titulo,
        prioridade=dados.prioridade,
        prazo=dados.prazo,
    )


@router.get(
    "",
    response_model=list[TarefaOut],
    summary="Listar as tarefas do usuário logado",
)
def listar_tasks(
    usuario: UsuarioAtual,
    servico: Servico,
    response: Response,
    # `status_tarefa` (e não `status`): o arquivo já importa `status` do FastAPI.
    # O alias="status" mantém o nome público na URL.
    status_tarefa: Annotated[StatusTarefa | None, Query(alias="status")] = None,
    prioridade: Annotated[PrioridadeTarefa | None, Query()] = None,
    prazo_ate: Annotated[
        date | None,
        Query(alias="prazoAte", description="Somente tarefas com prazo até esta data"),
    ] = None,
    busca: Annotated[
        str | None,
        Query(max_length=200, description="Texto contido no título (sem diferenciar maiúsculas)"),
    ] = None,
) -> list[TarefaOut]:
    """Lista as tarefas do usuário logado, com filtros opcionais.

    Os filtros se combinam (todos precisam valer ao mesmo tempo). As tarefas
    saem das mais recentes para as mais antigas, e o cabeçalho `X-Total-Count`
    traz a quantidade encontrada.

    Se nenhuma tarefa atender aos critérios, a resposta é uma lista vazia — e
    não 404: a coleção existe, apenas está vazia.
    """
    filtro = FiltroDeTarefas(
        usuario_id=usuario.id,
        status=status_tarefa,
        prioridade=prioridade,
        prazo_ate=prazo_ate,
        busca=(busca or "").strip() or None,
    )
    tarefas = servico.listar(filtro)
    response.headers["X-Total-Count"] = str(len(tarefas))
    return tarefas


@router.get(
    "/{tarefa_id}",
    response_model=TarefaOut,
    summary="Consultar uma tarefa",
    responses=_RESPOSTAS_DE_UMA_TAREFA,
)
def buscar_task(tarefa_id: int, usuario: UsuarioAtual, servico: Servico) -> TarefaOut:
    """Devolve uma tarefa do usuário logado."""
    return servico.buscar(tarefa_id, usuario.id)


@router.patch(
    "/{tarefa_id}",
    response_model=TarefaOut,
    summary="Atualizar tarefa",
    responses=_RESPOSTAS_DE_UMA_TAREFA,
)
def atualizar_task(
    tarefa_id: int, dados: TarefaUpdate, usuario: UsuarioAtual, servico: Servico
) -> TarefaOut:
    """Atualiza parcialmente uma tarefa: só os campos enviados mudam.

    Quando o status muda, a data de conclusão é ajustada pela própria tarefa,
    conforme a RN-03.
    """
    return servico.atualizar(tarefa_id, usuario.id, _montar_alteracoes(dados))


@router.delete(
    "/{tarefa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover tarefa",
    responses=_RESPOSTAS_DE_UMA_TAREFA,
)
def remover_task(tarefa_id: int, usuario: UsuarioAtual, servico: Servico) -> Response:
    """Remove uma tarefa definitivamente."""
    servico.remover(tarefa_id, usuario.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
