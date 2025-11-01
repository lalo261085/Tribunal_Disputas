"""JSON API for managing disputes and votes."""

from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request


api_bp = Blueprint("api", __name__)


def _repo():
    return current_app.config["DATA_REPOSITORY"]


def _forbidden_words() -> tuple[str, ...]:
    return current_app.config.get("FORBIDDEN_WORDS", ("insulto1", "insulto2"))


@api_bp.before_request
def _require_api_token():
    token = current_app.config.get("API_TOKEN")
    if not token:
        return None
    provided = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").removeprefix("Bearer ")
    if provided != token:
        return jsonify({"error": "Unauthorized"}), 401
    return None


def _ensure_user(data: dict, username: str) -> dict:
    for user in data["usuarios"]:
        if user["nombre"].lower() == username.lower():
            return user
    next_id = (data["usuarios"][-1]["id"] + 1) if data["usuarios"] else 1
    user = {"id": next_id, "nombre": username, "password": None}
    data["usuarios"].append(user)
    return user


def _serialize_dispute(conflicto: dict, data: dict) -> dict:
    comentarios = data["comentarios"].get(str(conflicto["id"]), [])
    return {
        **conflicto,
        "comentarios": comentarios,
    }


@api_bp.get("/disputes")
def list_disputes():
    repo = _repo()
    data = repo.load_data()
    repo.advance_conflict_phases(data, datetime.now())
    data = repo.load_data()
    return jsonify({
        "disputes": [_serialize_dispute(c, data) for c in data["conflictos"]],
    })


@api_bp.get("/disputes/<int:conflicto_id>")
def get_dispute(conflicto_id: int):
    repo = _repo()
    data = repo.load_data()
    conflicto = next((c for c in data["conflictos"] if c["id"] == conflicto_id), None)
    if not conflicto:
        return jsonify({"error": "Dispute not found"}), 404
    repo.advance_conflict_phases(data, datetime.now())
    data = repo.load_data()
    conflicto = next((c for c in data["conflictos"] if c["id"] == conflicto_id), None)
    return jsonify(_serialize_dispute(conflicto, data))


@api_bp.post("/disputes")
def create_dispute():
    payload = request.get_json(silent=True) or {}
    required = {"creator", "descripcion", "descripcion_parte_a", "descripcion_parte_b"}
    if not required.issubset(payload):
        return jsonify({"error": "Missing required fields"}), 400

    repo = _repo()
    data = repo.load_data()
    creator_name = payload["creator"].strip()
    if not creator_name:
        return jsonify({"error": "Creator is required"}), 400
    creator = _ensure_user(data, creator_name)

    nuevo_id = (data["conflictos"][-1]["id"] + 1) if data["conflictos"] else 1
    inicio_votacion = datetime.now()
    voting_window = current_app.config.get("VOTING_WINDOW_HOURS", 24)
    conflicto = {
        "id": nuevo_id,
        "usuario_id": creator["id"],
        "descripcion": payload["descripcion"].strip(),
        "descripcion_parte_a": payload["descripcion_parte_a"].strip(),
        "descripcion_parte_b": payload["descripcion_parte_b"].strip(),
        "votos_parte_a": 0,
        "votos_parte_b": 0,
        "etapa": "votacion",
        "inicio_votacion": inicio_votacion.strftime("%Y-%m-%dT%H:%M:%S"),
        "fin_votacion": (inicio_votacion + timedelta(hours=voting_window)).strftime("%Y-%m-%dT%H:%M:%S"),
    }
    data["conflictos"].append(conflicto)
    repo.save_data(data)
    return jsonify(_serialize_dispute(conflicto, data)), 201


@api_bp.post("/disputes/<int:conflicto_id>/vote")
def vote_dispute(conflicto_id: int):
    payload = request.get_json(silent=True) or {}
    voto = payload.get("voto")
    username = (payload.get("usuario") or "").strip()
    if voto not in {"A", "B"} or not username:
        return jsonify({"error": "Invalid vote payload"}), 400

    repo = _repo()
    data = repo.load_data()
    conflicto = next((c for c in data["conflictos"] if c["id"] == conflicto_id), None)
    if not conflicto:
        return jsonify({"error": "Dispute not found"}), 404

    repo.advance_conflict_phases(data, datetime.now())
    data = repo.load_data()
    conflicto = next((c for c in data["conflictos"] if c["id"] == conflicto_id), None)
    if conflicto["etapa"] != "votacion":
        return jsonify({"error": "Voting is closed"}), 409

    user = _ensure_user(data, username)
    if any(v["usuario_id"] == user["id"] and v["conflicto_id"] == conflicto_id for v in data["votos"]):
        return jsonify({"error": "User already voted"}), 409

    data["votos"].append({
        "usuario_id": user["id"],
        "conflicto_id": conflicto_id,
        "voto": voto,
    })
    if voto == "A":
        conflicto["votos_parte_a"] += 1
    else:
        conflicto["votos_parte_b"] += 1

    repo.save_data(data)
    return jsonify(_serialize_dispute(conflicto, data)), 200


@api_bp.post("/disputes/<int:conflicto_id>/comments")
def add_comment(conflicto_id: int):
    payload = request.get_json(silent=True) or {}
    comentario = (payload.get("comentario") or "").strip()
    username = (payload.get("usuario") or "").strip()
    if not comentario or not username:
        return jsonify({"error": "Invalid comment payload"}), 400

    repo = _repo()
    data = repo.load_data()
    conflicto = next((c for c in data["conflictos"] if c["id"] == conflicto_id), None)
    if not conflicto:
        return jsonify({"error": "Dispute not found"}), 404

    repo.advance_conflict_phases(data, datetime.now())
    data = repo.load_data()
    conflicto = next((c for c in data["conflictos"] if c["id"] == conflicto_id), None)
    if conflicto["etapa"] != "debate":
        return jsonify({"error": "Debate is not active"}), 409

    user = _ensure_user(data, username)
    usuario_voto = next(
        (v["voto"] for v in data["votos"] if v["usuario_id"] == user["id"] and v["conflicto_id"] == conflicto_id),
        None,
    )

    votos_a = conflicto.get("votos_parte_a", 0)
    votos_b = conflicto.get("votos_parte_b", 0)
    if votos_a > votos_b:
        perdedor = "B"
    elif votos_b > votos_a:
        perdedor = "A"
    else:
        perdedor = None

    if not usuario_voto or (perdedor and usuario_voto != perdedor):
        return jsonify({"error": "Only voters from the losing side may comment"}), 403

    if any(palabra in comentario.lower() for palabra in _forbidden_words()):
        return jsonify({"error": "Comment contains forbidden words"}), 422

    data["comentarios"].setdefault(str(conflicto_id), []).append({
        "usuario": user["nombre"],
        "texto": comentario,
    })
    repo.save_data(data)

    return jsonify(_serialize_dispute(conflicto, data)), 201
