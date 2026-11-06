"""Provedores de dependência: montam os objetos que as rotas usam."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import obter_configuracao
from app.core.exceptions import NaoAutenticado
from app.core.security import HashBcrypt, HashDeSenha, TokenJWT
from app.db.database import obter_sessao
from app.models import Usuario
from app.repositories import UsuarioRepositorio
from app.services import UsuarioServico

# auto_error=False: sem este ajuste, o próprio FastAPI responderia à falta de
# token, num formato diferente do resto da API. Assim, a falta de token vira
# NaoAutenticado e passa pelo mesmo tratador de todos os erros (o do main.py).
_esquema_bearer = HTTPBearer(auto_error=False, description="Token recebido no login")


def obter_hasher() -> HashDeSenha:
    return HashBcrypt()


def obter_tokens() -> TokenJWT:
    config = obter_configuracao()
    return TokenJWT(config.segredo_jwt(), config.jwt_expira_minutos)


def obter_usuario_servico(
    sessao: Session = Depends(obter_sessao),
    hasher: HashDeSenha = Depends(obter_hasher),
    tokens: TokenJWT = Depends(obter_tokens),
) -> UsuarioServico:
    return UsuarioServico(UsuarioRepositorio(sessao), hasher, tokens)


def obter_usuario_atual(
    credenciais: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_esquema_bearer)
    ],
    servico: Annotated[UsuarioServico, Depends(obter_usuario_servico)],
) -> Usuario:
    """Identifica quem está fazendo a requisição, a partir do token."""
    if credenciais is None:
        raise NaoAutenticado()

    return servico.usuario_do_token(credenciais.credentials)


# Atalho para as rotas: `usuario: UsuarioAtual` significa "esta rota exige
# login, e o usuário logado chega pronto neste parâmetro".
UsuarioAtual = Annotated[Usuario, Depends(obter_usuario_atual)]