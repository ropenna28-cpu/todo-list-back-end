from __future__ import annotations
from collections.abc import Generator
from typing import Any
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import obter_configuracao

def _opcoes_do_engine(url: str) -> dict[str, Any]:
    if url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    return {"pool_pre_ping": True}

_url = obter_configuracao().url_banco

Base = declarative_base()
engine = create_engine(_url, echo=False, **_opcoes_do_engine(_url))
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def criar_tabelas() -> None:
    from app import models
    Base.metadata.create_all(bind=engine)

def obter_sessao() -> Generator[Session, None, None]:
    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()
