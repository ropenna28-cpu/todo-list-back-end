
"""Exceções de domínio."""
from __future__ import annotations


class ErroDeDominio(Exception):
    """Classe base de todo erro previsto de negócio."""
    mensagem = "Não foi possível concluir a operação."

    def __init__(self, mensagem: str | None = None) -> None:
        self.mensagem = mensagem or type(self).mensagem
        super().__init__(self.mensagem)


# Recurso inexistente: a camada HTTP traduz esta família em 404.
class RecursoNaoEncontrado(ErroDeDominio):
    """Pediram um registro que não existe."""
    mensagem = "Recurso não encontrado."


class UsuarioNaoEncontrado(RecursoNaoEncontrado):
    mensagem = "Usuário não encontrado."


class TarefaNaoEncontrada(RecursoNaoEncontrado):
    mensagem = "Tarefa não encontrada."


# Regra de negócio violada: a camada HTTP traduz esta família em 422.
class RegraDeNegocioViolada(ErroDeDominio):
    """A operação é compreensível, mas contraria uma regra do negócio."""
    mensagem = "Operação recusada por uma regra de negócio."


class TituloObrigatorio(RegraDeNegocioViolada):
    mensagem = "O título da tarefa não pode ficar vazio."


class ValorInvalido(RegraDeNegocioViolada):
    """Valor fora do conjunto aceito por um campo do domínio."""
    mensagem = "Valor inválido para o campo."


# Conflito: a camada HTTP traduz em 409.
class EmailJaCadastrado(ErroDeDominio):
    """RN-01: um e-mail não pode ser usado por dois usuários."""
    mensagem = "Já existe uma conta com este e-mail."


# Autorização: a camada HTTP traduz em 403.
class AcessoNaoAutorizado(ErroDeDominio):
    """Tentativa de mexer em uma tarefa que pertence a outro usuário."""
    mensagem = "Esta tarefa pertence a outro usuário."


# Autenticação: a camada HTTP traduz esta família em 401.
class NaoAutenticado(ErroDeDominio):
    """Usuário não autenticado ou sessão inválida."""
    mensagem = "É preciso entrar na conta para continuar."


class CredenciaisInvalidas(NaoAutenticado):
    """E-mail ou senha incorretos."""
    mensagem = "E-mail ou senha incorretos."


class TokenInvalido(NaoAutenticado):
    """Token inválido ou expirado."""
    mensagem = "Sessão inválida. Entre novamente."
