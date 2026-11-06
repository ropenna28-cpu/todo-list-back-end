
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import obter_configuracao
from app.core.security import HashBcrypt, HashDeSenha, TokenJWT
from app.db.database import obter_sessao
from app.repositories import UsuarioRepositorio
from app.services import UsuarioServico


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
