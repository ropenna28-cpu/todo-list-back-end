"""Dias 1 a 5: status, cadastro, erros em português, login e rota protegida."""

from conftest import autenticar, cadastrar


def test_raiz_responde(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["mensagem"] == "Todo List API no ar"
    assert r.json()["documentacao"] == "/docs"


def test_documentacao_abre(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_cadastro_devolve_201_sem_senha_e_em_camel_case(client):
    r = cadastrar(client)
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["nome"] == "Ana"
    assert corpo["email"] == "ana@exemplo.com"
    assert "criadoEm" in corpo and corpo["criadoEm"].endswith(("Z", "+00:00"))
    assert "senha" not in corpo and "senhaHash" not in corpo and "senha_hash" not in corpo


def test_email_repetido_da_409_mesmo_com_caixa_diferente(client):
    cadastrar(client)
    r = cadastrar(client, email="  ANA@Exemplo.com ")
    assert r.status_code == 409
    assert r.json()["detail"] == "Já existe uma conta com este e-mail."


def test_erros_de_validacao_em_portugues(client):
    r = client.post("/usuarios", json={"nome": "Ana", "senha": "senha123"})
    assert r.status_code == 422
    assert r.json()["detail"] == "O campo 'email' é obrigatório."

    r = client.post("/usuarios", json={"nome": "Ana", "email": "a@b.com", "senha": "123"})
    assert r.status_code == 422
    assert "precisa ter pelo menos 6 caractere(s)" in r.json()["detail"]

    r = cadastrar(client, nome="   ")
    assert r.status_code == 422 or r.status_code == 500  # ver teste abaixo
    # nome só com espaços é recusado pelo modelo (ValorInvalido -> 422)
    assert r.status_code == 422
    assert r.json()["detail"] == "O nome do usuário não pode ficar vazio."


def test_login_ok_e_credenciais_invalidas(client):
    cadastrar(client)
    r = client.post("/usuarios/login", json={"email": "ana@exemplo.com", "senha": "senha123"})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["tokenType"] == "bearer"
    assert corpo["accessToken"] and corpo["expiraEm"]
    assert corpo["usuario"]["email"] == "ana@exemplo.com"

    senha_errada = client.post("/usuarios/login", json={"email": "ana@exemplo.com", "senha": "errada!"})
    email_inexistente = client.post("/usuarios/login", json={"email": "x@y.com", "senha": "senha123"})
    for r in (senha_errada, email_inexistente):
        assert r.status_code == 401
        assert r.json()["detail"] == "E-mail ou senha incorretos."
        assert r.headers["www-authenticate"] == "Bearer"


def test_me_exige_token(client):
    r = client.get("/usuarios/me")
    assert r.status_code == 401
    assert r.json()["detail"] == "É preciso entrar na conta para continuar."
    assert r.headers["www-authenticate"] == "Bearer"


def test_me_com_token_valido_e_adulterado(client):
    h = autenticar(client)
    r = client.get("/usuarios/me", headers=h)
    assert r.status_code == 200
    assert r.json()["email"] == "ana@exemplo.com"

    token = h["Authorization"].split()[1]
    adulterado = {"Authorization": f"Bearer {token[:-4]}AAAA"}
    r = client.get("/usuarios/me", headers=adulterado)
    assert r.status_code == 401
    assert r.json()["detail"] == "Sessão inválida. Entre novamente."
