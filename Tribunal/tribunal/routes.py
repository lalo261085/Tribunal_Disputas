"""Flask routes for the Tribunal application."""

from __future__ import annotations

from datetime import datetime, timedelta

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .auth import login_required
from .sockets import socketio


bp = Blueprint("web", __name__)


def _data_repo():
    return current_app.config["DATA_REPOSITORY"]


def _forbidden_words() -> tuple[str, ...]:
    return current_app.config.get("FORBIDDEN_WORDS", ("insulto1", "insulto2"))


@bp.route("/", methods=["GET", "POST"])
def index():
    data = _data_repo().load_data()
    now = datetime.now()
    _data_repo().advance_conflict_phases(data, now)
    return render_template("index.html", conflictos=data["conflictos"], ahora=now, data=data)


@bp.route("/registrarse", methods=["GET", "POST"])
def registrarse():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        password = request.form.get("password", "")
        if not nombre or not password:
            flash("Nombre y contrase?a son obligatorios.", "error")
            return render_template("registrarse.html")

        data = _data_repo().load_data()
        if any(u["nombre"].lower() == nombre.lower() for u in data["usuarios"]):
            flash("El nombre de usuario ya est? en uso.", "error")
            return render_template("registrarse.html")

        usuario_id = (data["usuarios"][-1]["id"] + 1) if data["usuarios"] else 1
        data["usuarios"].append({
            "id": usuario_id,
            "nombre": nombre,
            "password": generate_password_hash(password),
        })
        cid = _data_repo().save_data(data)
        if cid:
            socketio.emit("data_updated", {"cid": cid})
        flash("Usuario registrado con ?xito. Ahora puedes iniciar sesi?n.", "success")
        return redirect(url_for("web.login"))
    return render_template("registrarse.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre = request.form.get("nombre", "")
        password = request.form.get("password", "")
        data = _data_repo().load_data()
        user = next((u for u in data["usuarios"] if u["nombre"].lower() == nombre.lower()), None)
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["nombre"]
            flash("Inicio de sesi?n exitoso.", "success")
            return redirect(url_for("web.index"))
        flash("Nombre de usuario o contrase?a incorrectos.", "error")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesi?n.", "success")
    return redirect(url_for("web.index"))


@bp.route("/agregar_conflicto", methods=["GET", "POST"])
@login_required
def agregar_conflicto():
    if request.method == "POST":
        descripcion = request.form.get("descripcion", "").strip()
        desc_a = request.form.get("descripcion_parte_a", "").strip()
        desc_b = request.form.get("descripcion_parte_b", "").strip()

        if any(len(texto) > 500 for texto in (descripcion, desc_a, desc_b)):
            flash("Cada descripci?n debe tener menos de 500 caracteres.", "error")
            return render_template("agregar_conflicto.html")

        data = _data_repo().load_data()
        nuevo_id = (data["conflictos"][-1]["id"] + 1) if data["conflictos"] else 1
        inicio_votacion = datetime.now()
        conflicto = {
            "id": nuevo_id,
            "usuario_id": session["user_id"],
            "descripcion": descripcion,
            "descripcion_parte_a": desc_a,
            "descripcion_parte_b": desc_b,
            "votos_parte_a": 0,
            "votos_parte_b": 0,
            "etapa": "votacion",
            "inicio_votacion": inicio_votacion.strftime("%Y-%m-%dT%H:%M:%S"),
            "fin_votacion": (inicio_votacion + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S"),
        }
        data["conflictos"].append(conflicto)
        cid = _data_repo().save_data(data)
        if cid:
            socketio.emit("data_updated", {"cid": cid})
        flash("Conflicto agregado. Votaci?n abierta por 24 horas.", "success")
        return redirect(url_for("web.index"))
    return render_template("agregar_conflicto.html")


@bp.route("/borrar_conflicto/<int:conflicto_id>", methods=["POST"])
@login_required
def borrar_conflicto(conflicto_id: int):
    data = _data_repo().load_data()
    conflicto = next((c for c in data["conflictos"] if c["id"] == conflicto_id), None)
    if not conflicto:
        flash("El conflicto no existe.", "error")
    elif conflicto["usuario_id"] != session["user_id"]:
        flash("Solo puedes borrar tus propios conflictos.", "error")
    else:
        data["conflictos"] = [c for c in data["conflictos"] if c["id"] != conflicto_id]
        data["votos"] = [v for v in data["votos"] if v["conflicto_id"] != conflicto_id]
        data["comentarios"].pop(str(conflicto_id), None)
        cid = _data_repo().save_data(data)
        if cid:
            socketio.emit("data_updated", {"cid": cid})
        flash("Conflicto eliminado con ?xito.", "success")
    return redirect(url_for("web.index"))


@bp.route("/votar/<int:conflicto_id>", methods=["POST"])
@login_required
def votar(conflicto_id: int):
    voto = request.form.get("voto")
    data = _data_repo().load_data()
    for conflicto in data["conflictos"]:
        if conflicto["id"] == conflicto_id and conflicto["etapa"] == "votacion":
            if any(v["usuario_id"] == session["user_id"] and v["conflicto_id"] == conflicto_id for v in data["votos"]):
                flash("Ya votaste en este conflicto.", "error")
            else:
                data["votos"].append({
                    "usuario_id": session["user_id"],
                    "conflicto_id": conflicto_id,
                    "voto": voto,
                })
                if voto == "A":
                    conflicto["votos_parte_a"] += 1
                elif voto == "B":
                    conflicto["votos_parte_b"] += 1
                cid = _data_repo().save_data(data)
                if cid:
                    socketio.emit("data_updated", {"cid": cid})
                flash("Voto registrado con ?xito.", "success")
            break
    else:
        flash("La votaci?n no est? activa para este conflicto.", "error")
    return redirect(url_for("web.index"))


@bp.route("/debate/<int:conflicto_id>", methods=["GET", "POST"])
@login_required
def debate(conflicto_id: int):
    data = _data_repo().load_data()
    conflicto = next((c for c in data["conflictos"] if c["id"] == conflicto_id), None)
    if not conflicto or conflicto.get("etapa") != "debate":
        flash("El debate no est? activo para este conflicto.", "error")
        return redirect(url_for("web.index"))

    votos_a = conflicto.get("votos_parte_a", 0)
    votos_b = conflicto.get("votos_parte_b", 0)
    if votos_a > votos_b:
        ganador, perdedor = "A", "B"
    elif votos_b > votos_a:
        ganador, perdedor = "B", "A"
    else:
        ganador, perdedor = "Empate", None

    usuario_voto = next(
        (v["voto"] for v in data["votos"] if v["usuario_id"] == session["user_id"] and v["conflicto_id"] == conflicto_id),
        None,
    )

    if request.method == "POST":
        comentario = request.form.get("comentario", "").strip()
        if not usuario_voto or (perdedor and usuario_voto != perdedor):
            flash("Solo quienes votaron por la postura perdedora pueden comentar.", "error")
        elif any(palabra in comentario.lower() for palabra in _forbidden_words()):
            flash("Comentario contiene palabras no permitidas.", "error")
        else:
            data["comentarios"].setdefault(str(conflicto_id), []).append({
                "usuario": session.get("username"),
                "texto": comentario,
            })
            cid = _data_repo().save_data(data)
            if cid:
                socketio.emit("data_updated", {"cid": cid})
            flash("Comentario agregado con ?xito.", "success")

    comentarios = data["comentarios"].get(str(conflicto_id), [])
    return render_template(
        "debate.html",
        conflicto=conflicto,
        comentarios=comentarios,
        ganador=ganador,
        perdedor=perdedor,
        conflicto_id=conflicto_id,
        ahora=datetime.now(),
    )
