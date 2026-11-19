"""Dias 6 a 10: criar, listar, consultar, editar, excluir, concluir e filtrar tarefas."""

from datetime import date, timedelta

from conftest import autenticar


def criar(client, h, **corpo):
    corpo.setdefault("titulo", "Estudar FastAPI")
    return client.post("/tasks", json=corpo, headers=h)


# ---------------------------------------------------------------- Dia 6
def test_criar_tarefa_nasce_pendente_e_do_dono_do_token(client):
    h = autenticar(client)
    r = criar(client, h, prioridade="alta", status="concluida", usuarioId=99)
    assert r.status_code == 201
    t = r.json()
    assert t["status"] == "pendente"
    assert t["prioridade"] == "alta"
    assert t["usuarioId"] != 99
    assert t["concluidoEm"] is None
    assert t["criadoEm"].endswith(("Z", "+00:00"))


def test_criar_tarefa_erros(client):
    h = autenticar(client)
    r = criar(client, h, titulo=" ")
    assert r.status_code == 422
    assert r.json()["detail"] == "O título da tarefa não pode ficar vazio." or "pelo menos 1" in r.json()["detail"]

    r = criar(client, h, prioridade="altissima")
    assert r.status_code == 422
    assert "baixa" in r.json()["detail"] and "urgente" in r.json()["detail"]

    assert client.post("/tasks", json={"titulo": "x"}).status_code == 401


# ---------------------------------------------------------------- Dia 7
def test_listar_so_as_minhas_em_ordem_do_mais_recente(client):
    ana = autenticar(client)
    bruno = autenticar(client, email="bruno@exemplo.com", nome="Bruno")

    r = client.get("/tasks", headers=ana)
    assert r.status_code == 200 and r.json() == []
    assert r.headers["x-total-count"] == "0"

    for n in range(3):
        criar(client, ana, titulo=f"tarefa {n}")
    criar(client, bruno, titulo="do bruno")

    r = client.get("/tasks", headers=ana)
    assert r.headers["x-total-count"] == "3"
    assert [t["titulo"] for t in r.json()] == ["tarefa 2", "tarefa 1", "tarefa 0"]

    r = client.get("/tasks", headers=bruno)
    assert [t["titulo"] for t in r.json()] == ["do bruno"]

    assert client.get("/tasks").status_code == 401


# ---------------------------------------------------------------- Dia 8
def test_consultar_editar_excluir_com_checagem_de_dono(client):
    ana = autenticar(client)
    bruno = autenticar(client, email="bruno@exemplo.com", nome="Bruno")
    prazo = (date.today() + timedelta(days=3)).isoformat()
    tid = criar(client, ana, titulo="Original", prazo=prazo).json()["id"]

    assert client.get(f"/tasks/{tid}", headers=ana).status_code == 200

    r = client.patch(f"/tasks/{tid}", json={"titulo": "Novo título"}, headers=ana)
    assert r.status_code == 200
    assert r.json()["titulo"] == "Novo título" and r.json()["prazo"] == prazo

    r = client.patch(f"/tasks/{tid}", json={"prazo": None}, headers=ana)
    assert r.status_code == 200 and r.json()["prazo"] is None

    for metodo in ("get", "patch", "delete"):
        kw = {"json": {"titulo": "invasor"}} if metodo == "patch" else {}
        r = getattr(client, metodo)(f"/tasks/{tid}", headers=bruno, **kw)
        assert r.status_code == 403, metodo
        assert r.json()["detail"] == "Esta tarefa pertence a outro usuário."
    assert client.get(f"/tasks/{tid}", headers=ana).json()["titulo"] == "Novo título"

    r = client.get("/tasks/9999", headers=ana)
    assert r.status_code == 404 and r.json()["detail"] == "Tarefa não encontrada."

    r = client.get("/tasks/abc", headers=ana)
    assert r.status_code == 422
    assert r.json()["detail"] == "O campo 'tarefa_id' precisa ser um número inteiro."

    r = client.delete(f"/tasks/{tid}", headers=ana)
    assert r.status_code == 204 and r.content == b""
    assert client.delete(f"/tasks/{tid}", headers=ana).status_code == 404


# ---------------------------------------------------------------- Dia 9
def test_concluir_e_reabrir_controlam_a_data(client):
    h = autenticar(client)
    tid = criar(client, h).json()["id"]

    r = client.patch(f"/tasks/{tid}", json={"status": "concluida"}, headers=h)
    assert r.json()["status"] == "concluida"
    data = r.json()["concluidoEm"]
    assert data is not None

    r = client.patch(f"/tasks/{tid}", json={"titulo": "editada depois"}, headers=h)
    assert r.json()["concluidoEm"] == data

    r = client.patch(f"/tasks/{tid}", json={"status": "concluida"}, headers=h)
    assert r.json()["concluidoEm"] == data  # RN-03: não falsifica a data

    r = client.patch(f"/tasks/{tid}", json={"status": "pendente"}, headers=h)
    assert r.json()["status"] == "pendente" and r.json()["concluidoEm"] is None

    r = client.patch(f"/tasks/{tid}", json={"status": "concluida"}, headers=h)
    assert r.json()["concluidoEm"] is not None

    r = client.patch(f"/tasks/{tid}", json={"status": "arquivada"}, headers=h)
    assert r.status_code == 422
    assert "pendente" in r.json()["detail"] and "concluida" in r.json()["detail"]


# --------------------------------------------------------------- Dia 10
def test_filtros_e_busca(client):
    h = autenticar(client)
    hoje = date.today()
    dias = lambda n: (hoje + timedelta(days=n)).isoformat()  # noqa: E731

    primeira = criar(client, h, titulo="Organizar planilha de gastos", prioridade="alta", prazo=dias(2)).json()["id"]
    criar(client, h, titulo="Atualizar a PLANILHA de notas", prioridade="baixa", prazo=dias(20))
    criar(client, h, titulo="Aumentar 10% das vendas", prioridade="urgente", prazo=dias(5))
    criar(client, h, titulo="Comprar presente", prioridade="alta")
    client.patch(f"/tasks/{primeira}", json={"status": "concluida"}, headers=h)

    def consulta(**params):
        r = client.get("/tasks", params=params, headers=h)
        return r, [t["titulo"] for t in r.json()] if r.status_code == 200 else None

    r, t = consulta()
    assert r.headers["x-total-count"] == "4"

    r, t = consulta(status="pendente")
    assert r.headers["x-total-count"] == "3"

    r, t = consulta(prioridade="alta")
    assert r.headers["x-total-count"] == "2"

    r, t = consulta(status="pendente", prioridade="alta")
    assert t == ["Comprar presente"]

    r, t = consulta(busca="PLANILHA")
    assert r.headers["x-total-count"] == "2"

    r, t = consulta(busca="%")
    assert t == ["Aumentar 10% das vendas"]

    r, t = consulta(prazoAte=dias(7))
    assert r.headers["x-total-count"] == "2"
    assert "Comprar presente" not in t

    r, t = consulta(busca="   ")
    assert r.headers["x-total-count"] == "4"

    r, _ = consulta(prioridade="altissima")
    assert r.status_code == 422 and "urgente" in r.json()["detail"]

    r, _ = consulta(prazoAte="31/12/2026")
    assert r.status_code == 422
