
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt import InvalidTokenError, ExpiredSignatureError


LIMITE_BYTES_SENHA = 72


class HashDeSenha(ABC):
    @abstractmethod
    def gerar(self, senha: str) -> str:
        pass

    @abstractmethod
    def verificar(self, senha: str, hash_armazenado: str) -> bool:
        pass


class HashBcrypt(HashDeSenha):
    def gerar(self, senha: str) -> str:
        return bcrypt.hashpw(
            senha.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("ascii")

    def verificar(self, senha: str, hash_armazenado: str) -> bool:
        senha_bytes = senha.encode("utf-8")

        if len(senha_bytes) > LIMITE_BYTES_SENHA:
            return False

        return bcrypt.checkpw(
            senha_bytes,
            hash_armazenado.encode("ascii"),
        )


@dataclass(frozen=True)
class TokenEmitido:
    valor: str
    expira_em: datetime


class TokenJWT:
    """Emite e valida tokens JWT."""

    def __init__(self, segredo: str, expira_minutos: int = 120) -> None:
        self._segredo = segredo
        self._expira_minutos = expira_minutos

    def emitir(
        self,
        usuario_id: int,
        agora: datetime | None = None,
    ) -> TokenEmitido:
        instante = agora or datetime.now(timezone.utc)
        expira_em = instante + timedelta(minutes=self._expira_minutos)

        payload = {
            "sub": str(usuario_id),
            "exp": expira_em,
        }

        valor = jwt.encode(
            payload,
            self._segredo,
            algorithm="HS256",
        )

        return TokenEmitido(
            valor=valor,
            expira_em=expira_em,
        )

    def ler(self, token: str) -> dict:
        from app.core.exceptions import TokenInvalido

        try:
            payload = jwt.decode(
                token,
                self._segredo,
                algorithms=["HS256"],
            )

            if "sub" not in payload or "exp" not in payload:
                raise TokenInvalido()

            return payload

        except (ExpiredSignatureError, InvalidTokenError):
            raise TokenInvalido() from None
