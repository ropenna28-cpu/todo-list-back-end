"""Repositórios: a única camada que conversa com o banco de dados.

Antes, as consultas ficavam dentro das funções de rota. Isso misturava três
assuntos numa função só — HTTP, regra de negócio e SQL.

Com os repositórios, a regra passa a ser: serviço não sabe SQL, rota não sabe
banco. Quem precisa de dados pede a um repositório.
"""

from app.repositories.base import RepositorioBase
from app.repositories.tarefa import FiltroDeTarefas, PaginaDeTarefas, TarefaRepositorio
from app.repositories.usuario import UsuarioRepositorio

__all__ = [
    "FiltroDeTarefas",
    "PaginaDeTarefas",
    "RepositorioBase",
    "TarefaRepositorio",
    "UsuarioRepositorio",
]
