"""Operações de cadastro, login e identificação de usuários."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import (
    CredenciaisInvalidas,
    EmailJaCadastrado,
    TokenInvalido,
)
from app.core.security import HashDeSenha, TokenEmitido, TokenJWT
from app.models import Usuario
from app.repositories import UsuarioRepositorio


@dataclass(frozen=True)
class Sessao:
    usuario: Usuario
    token: TokenEmitido


class UsuarioServico:
    """Operações de cadastro e login de usuários."""

    def __init__(
        self,
        repositorio: UsuarioRepositorio,
        hasher: HashDeSenha,
        tokens: TokenJWT | None = None,
    ) -> None:
        self._repositorio = repositorio
        self._hasher = hasher
        self._tokens = tokens

    def cadastrar(self, nome: str, email: str, senha: str) -> Usuario:
        """Cadastra um usuário com a senha protegida por hash.

        Raises:
            EmailJaCadastrado: se o e-mail já estiver em uso (RN-01).
        """
        if self._repositorio.email_existe(email):
            raise EmailJaCadastrado()

        usuario = Usuario(nome=nome, email=email)
        usuario.definir_senha(senha, self._hasher)
        return self._repositorio.salvar(usuario)

    def autenticar(self, email: str, senha: str) -> Usuario:
        """Confere as credenciais do usuário."""
        usuario = self._repositorio.buscar_por_email(email)

        if usuario is None or not usuario.senha_confere(senha, self._hasher):
            raise CredenciaisInvalidas()

        return usuario

    def entrar(self, email: str, senha: str) -> Sessao:
        """Autentica o usuário e emite seu token de acesso."""
        usuario = self.autenticar(email, senha)

        return Sessao(
            usuario=usuario,
            token=self._exigir_tokens().emitir(usuario.id),
        )

    def usuario_do_token(self, token: str) -> Usuario:
        """Devolve o dono de um token válido.

        Raises:
            TokenInvalido: se o token for inválido ou estiver vencido, ou se
                pertencer a um usuário que não existe mais.
        """
        payload = self._exigir_tokens().ler(token)

        try:
            usuario_id = int(payload["sub"])
        except (KeyError, ValueError):
            raise TokenInvalido() from None

        usuario = self._repositorio.buscar_por_id(usuario_id)

        if usuario is None:
            raise TokenInvalido()

        return usuario

    def _exigir_tokens(self) -> TokenJWT:
        """Exige um emissor de tokens configurado."""
        if self._tokens is None:
            raise RuntimeError("O serviço não possui um emissor de tokens.")

        return self._tokens