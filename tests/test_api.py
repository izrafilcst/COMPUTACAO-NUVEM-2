import pytest
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})
    return app.test_client()


def test_health(client):
    result = client.get("/health")
    assert result.status_code == 200
    assert result.json["status"] == "ok"


def test_create_and_list(client):
    result = client.post("/tasks", json={"title": "Estudar GitHub Actions"})
    assert result.status_code == 201
    assert result.json["id"] == 1
    listed = client.get("/tasks")
    assert listed.status_code == 200
    assert len(listed.json) == 1
    assert listed.json[0]["title"] == "Estudar GitHub Actions"


def test_invalid_title(client):
    assert client.post("/tasks", json={"title": "  "}).status_code == 400


def test_mark_done(client):
    item = client.post("/tasks", json={"title": "Deploy"}).json
    result = client.patch(f'/tasks/{item["id"]}', json={"done": True})
    assert result.status_code == 200
    assert client.get("/tasks").json[0]["done"] is True


def test_not_found(client):
    assert client.patch("/tasks/999", json={"done": True}).status_code == 404


def test_version_default(client, monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    result = client.get("/version")
    assert result.status_code == 200
    assert result.json == {"version": "dev"}


def test_version_from_env(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "abc123")
    assert client.get("/version").json == {"version": "abc123"}


def test_delete_task(client):
    keep = client.post("/tasks", json={"title": "Manter"}).json
    gone = client.post("/tasks", json={"title": "Apagar"}).json
    result = client.delete(f'/tasks/{gone["id"]}')
    assert result.status_code == 204
    assert result.data == b""
    assert [t["id"] for t in client.get("/tasks").json] == [keep["id"]]


def test_delete_not_found(client):
    result = client.delete("/tasks/999")
    assert result.status_code == 404
    assert result.json["error"] == "tarefa nao encontrada"


def test_delete_twice_and_bad_id(client):
    item = client.post("/tasks", json={"title": "x"}).json
    assert client.delete(f'/tasks/{item["id"]}').status_code == 204
    assert client.delete(f'/tasks/{item["id"]}').status_code == 404
    assert client.delete("/tasks/abc").status_code == 404
