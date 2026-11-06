"""Endpoints de usuário: cadastro, login e "quem sou eu"."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import UsuarioAtual, obter_usuario_servico
from app.schemas import (
    SessaoOut,
    UsuarioCreate,
    UsuarioLogin,
    UsuarioOut,
)
from app.services import UsuarioServico


router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post(
    "",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar usuário",
    responses={409: {"description": "E-mail já cadastrado"}},
)
def cadastrar_usuario(
    dados: UsuarioCreate,
    servico: Annotated[UsuarioServico, Depends(obter_usuario_servico)],
) -> UsuarioOut:
    """
    Cadastra um novo usuário com a senha armazenada como hash.
    O cadastro não faz login automaticamente. Depois de criar a conta,
    o cliente deve chamar a rota de login.
    """
    return servico.cadastrar(dados.nome, dados.email, dados.senha)


@router.post(
    "/login",
    response_model=SessaoOut,
    summary="Entrar no sistema",
    responses={401: {"description": "E-mail ou senha incorretos"}},
)
def entrar(
    dados: UsuarioLogin,
    servico: Annotated[UsuarioServico, Depends(obter_usuario_servico)],
) -> SessaoOut:
    """
    Confere e-mail e senha e devolve o token de acesso e o usuário.
    No /docs, o token recebido aqui é usado pelo botão Authorize.
    """
    sessao = servico.entrar(dados.email, dados.senha)

    return SessaoOut(
        access_token=sessao.token.valor,
        expira_em=sessao.token.expira_em,
        usuario=UsuarioOut.model_validate(sessao.usuario),
    )


@router.get(
    "/me",
    response_model=UsuarioOut,
    summary="Consultar o usuário logado",
    responses={401: {"description": "Sem token, ou token inválido/expirado"}},
)
def quem_sou_eu(usuario: UsuarioAtual) -> UsuarioOut:
    """Devolve os dados de quem é dono do token."""
    return usuario