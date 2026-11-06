from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from sqlalchemy.orm import Session

Entidade = TypeVar("Entidade")

class RepositorioBase(ABC, Generic[Entidade]):
    def __init__(self, sessão: Session) -> None:
        self.sessao = sessão

    @property
    @abstractmethod
    def modelo(self) -> type[Entidade]:
        pass

    def buscar_por_id(self, identificador: int) -> Entidade | None:
        return self.sessao.get(self.modelo, identificador)

    def salvar(self, entidade: Entidade) -> Entidade:
        self.sessao.add(entidade)
        self.sessao.commit()
        self.sessao.refresh(entidade)
        return entidade

    def remover(self, entidade: Entidade) -> None:
        self.sessao.delete(entidade)
        self.sessao.commit()
