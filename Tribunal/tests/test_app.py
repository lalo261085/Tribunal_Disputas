from __future__ import annotations

from datetime import datetime, timedelta


def test_registration_and_login_flow(client, app):
    response = client.post(
        "/registrarse",
        data={"nombre": "alice", "password": "password123"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    response = client.post(
        "/login",
        data={"nombre": "alice", "password": "password123"},
        follow_redirects=True,
    )
    assert b"Inicio de sesi\xc3\xb3n exitoso" in response.data


def test_full_conflict_lifecycle(client, app):
    repo = app.config["DATA_REPOSITORY"]

    client.post("/registrarse", data={"nombre": "creator", "password": "secret123"}, follow_redirects=True)
    client.post("/login", data={"nombre": "creator", "password": "secret123"}, follow_redirects=True)

    client.post(
        "/agregar_conflicto",
        data={
            "descripcion": "Conflicto de prueba",
            "descripcion_parte_a": "Postura A",
            "descripcion_parte_b": "Postura B",
        },
        follow_redirects=True,
    )

    data = repo.load_data()
    assert len(data["conflictos"]) == 1
    conflicto_id = data["conflictos"][0]["id"]

    client.get("/logout", follow_redirects=True)
    client.post("/registrarse", data={"nombre": "votante", "password": "secret456"}, follow_redirects=True)
    client.post("/login", data={"nombre": "votante", "password": "secret456"}, follow_redirects=True)

    client.post(f"/votar/{conflicto_id}", data={"voto": "B"}, follow_redirects=True)

    data = repo.load_data()
    conflicto = data["conflictos"][0]
    conflicto["fin_votacion"] = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    conflicto["votos_parte_a"] = 2
    repo.save_data(data)
    repo.advance_conflict_phases(data, datetime.now())

    response = client.get(f"/debate/{conflicto_id}")
    assert response.status_code == 200

    response = client.post(
        f"/debate/{conflicto_id}",
        data={"comentario": "Comentario constructivo"},
        follow_redirects=True,
    )
    data = repo.load_data()
    comentarios = data["comentarios"].get(str(conflicto_id), [])
    assert any(com["texto"] == "Comentario constructivo" for com in comentarios)

    response = client.post(
        f"/debate/{conflicto_id}",
        data={"comentario": "insulto1 inadmisible"},
        follow_redirects=True,
    )
    data = repo.load_data()
    comentarios = data["comentarios"].get(str(conflicto_id), [])
    assert sum(1 for com in comentarios if com["texto"].startswith("insulto1")) == 0
