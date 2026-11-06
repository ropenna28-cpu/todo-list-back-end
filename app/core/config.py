
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class ConfiguracaoInvalida(RuntimeError):
    """Falta (ou está errada) uma variável de ambiente obrigatória."""


@dataclass(frozen=True)
class Configuracao:
    database_url: str = ""
    jwt_secret: str = ""
    jwt_expira_minutos: int = 120

    @classmethod
    def do_ambiente(cls) -> Configuracao:
        return cls(
            database_url=os.getenv("DATABASE_URL", "").strip(),
            jwt_secret=os.getenv("JWT_SECRET", "").strip(),
            jwt_expira_minutos=int(
                os.getenv("JWT_EXPIRA_MINUTOS", "120")
            ),
        )

    @property
    def url_banco(self) -> str:
        if not self.database_url:
            raise ConfiguracaoInvalida(
                "DATABASE_URL não definida. Copie o arquivo .env.example para .env"
            )
        return self.database_url

    def segredo_jwt(self) -> str:
        if len(self.jwt_secret) < 32:
            raise ConfiguracaoInvalida(
                "JWT_SECRET deve possuir pelo menos 32 caracteres."
            )
        return self.jwt_secret


@lru_cache
def obter_configuracao() -> Configuracao:
    return Configuracao.do_ambiente()
