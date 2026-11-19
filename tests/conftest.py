"""Configuração dos testes: banco SQLite em memória, isolado do todo_list.db."""

import os

# Precisa vir ANTES de qualquer import de `app`: o engine é criado na importação.
# O python-dotenv não sobrescreve variáveis que já existem no ambiente.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "segredo-de-teste-com-mais-de-32-caracteres-ok"
os.environ["JWT_EXPIRA_MINUTOS"] = "120"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    """Cliente HTTP com as tabelas recriadas do zero a cada teste."""
    with TestClient(app) as c:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        yield c


def cadastrar(client, nome="Ana", email="ana@exemplo.com", senha="senha123"):
    return client.post("/usuarios", json={"nome": nome, "email": email, "senha": senha})


def autenticar(client, email="ana@exemplo.com", senha="senha123", nome="Ana"):
    """Cadastra (se preciso), entra e devolve os cabeçalhos com o token."""
    cadastrar(client, nome=nome, email=email, senha=senha)
    r = client.post("/usuarios/login", json={"email": email, "senha": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['accessToken']}"}
