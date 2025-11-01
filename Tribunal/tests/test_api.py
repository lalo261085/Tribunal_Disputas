from __future__ import annotations

from datetime import datetime, timedelta

from tribunal import Settings, create_application


def test_api_dispute_flow(client, app):
    # Create dispute
    response = client.post(
        "/api/disputes",
        json={
            "creator": "creator",
            "descripcion": "Conflicto API",
            "descripcion_parte_a": "Parte A",
            "descripcion_parte_b": "Parte B",
        },
    )
    assert response.status_code == 201
    dispute = response.get_json()
    conflicto_id = dispute["id"]

    # Vote from two users
    response = client.post(
        f"/api/disputes/{conflicto_id}/vote",
        json={"usuario": "alice", "voto": "A"},
    )
    assert response.status_code == 200

    response = client.post(
        f"/api/disputes/{conflicto_id}/vote",
        json={"usuario": "bob", "voto": "B"},
    )
    assert response.status_code == 200

    repo = app.config["DATA_REPOSITORY"]
    data = repo.load_data()
    conflicto = next(c for c in data["conflictos"] if c["id"] == conflicto_id)
    conflicto["fin_votacion"] = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    repo.save_data(data)
    repo.advance_conflict_phases(data, datetime.now())

    response = client.post(
        f"/api/disputes/{conflicto_id}/comments",
        json={"usuario": "alice", "comentario": "Comentario constructivo"},
    )
    assert response.status_code == 201
    result = response.get_json()
    assert any(c["texto"] == "Comentario constructivo" for c in result["comentarios"])

    # Ensure listing returns updated structure
    response = client.get("/api/disputes")
    assert response.status_code == 200
    payload = response.get_json()
    assert any(d["id"] == conflicto_id for d in payload["disputes"])


def test_api_requires_token_when_configured(tmp_path):
    secure_settings = Settings(
        data_dir=tmp_path / "secure",
        api_token="secret",
        forbidden_words=("insulto1", "insulto2"),
    )
    secure_app = create_application(secure_settings)
    secure_client = secure_app.test_client()

    response = secure_client.get("/api/disputes")
    assert response.status_code == 401

    response = secure_client.get("/api/disputes", headers={"X-API-Key": "secret"})
    assert response.status_code == 200
