from flask import Flask, render_template, request, redirect, url_for, flash, session
from gestor import cargar_datos, guardar_datos
from datetime import date
import csv
from io import StringIO, BytesIO
from flask import send_file
from openpyxl import Workbook
import json
import os

# =========================
# USUARIOS
# =========================
ARCHIVO_USUARIOS = "usuarios.json"


def cargar_usuarios():
    if not os.path.exists(ARCHIVO_USUARIOS):
        return {}

    try:
        with open(ARCHIVO_USUARIOS, "r", encoding="utf-8") as f:
            contenido = f.read().strip()
            if not contenido:
                return {}
            return json.loads(contenido)
    except json.JSONDecodeError:
        return {}


def guardar_usuarios(usuarios):
    with open(ARCHIVO_USUARIOS, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)


# =========================
# APP
# =========================
app = Flask(__name__)
app.secret_key = "clave-secreta-simple"


# =========================
# UTILIDADES
# =========================
def calcular_resumen(mes_data):
    ingreso = mes_data["ingreso"]
    gastos_fijos = mes_data["gastos_fijos"]
    gastos_variables = mes_data["gastos_variables"]

    total_fijos = sum(g["importe"] for g in gastos_fijos)
    total_variables = sum(g["importe"] for g in gastos_variables)
    gasto_total = total_fijos + total_variables
    saldo = ingreso - gasto_total

    return {
        "ingreso": ingreso,
        "total_fijos": total_fijos,
        "total_variables": total_variables,
        "gasto_total": gasto_total,
        "saldo": saldo
    }


# =========================
# LOGIN / LOGOUT / REGISTRO
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    usuarios = cargar_usuarios()

    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        if usuario in usuarios and usuarios[usuario] == password:
            session.clear()
            session["usuario"] = usuario
            return redirect(url_for("inicio"))
        else:
            flash("Usuario o contraseña incorrectos")

    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    usuarios = cargar_usuarios()

    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        if usuario in usuarios:
            flash("Ese usuario ya existe")
            return redirect(url_for("registro"))

        usuarios[usuario] = password
        guardar_usuarios(usuarios)

        session.clear()
        session["usuario"] = usuario
        return redirect(url_for("inicio"))

    return render_template("registro.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================
# INICIO
# =========================
@app.route("/")
def inicio():
    if "usuario" not in session:
        return redirect(url_for("login"))

    usuario = session["usuario"]
    datos = cargar_datos(usuario)

    mes_actual = datos["mes_actual"]

    if not mes_actual:
        return render_template(
            "index.html",
            mensaje="No hay mes actual creado",
            mes_actual=None,
            gastos=[],
            meses=datos["meses"].keys(),
            resumen=None
        )

    mes_data = datos["meses"][mes_actual]

    gastos = sorted(
        mes_data["gastos_variables"],
        key=lambda g: g.get("fecha", "00/00"),
        reverse=True
    )

    resumen = calcular_resumen(mes_data)

    hoy = date.today()
    dia_hoy = f"{hoy.day:02d}"
    mes_hoy = f"{hoy.month:02d}"

    return render_template(
        "index.html",
        mensaje=f"Mes actual: {mes_actual}",
        mes_actual=mes_actual,
        gastos=gastos,
        meses=datos["meses"].keys(),
        resumen=resumen,
        dia_hoy=dia_hoy,
        mes_hoy=mes_hoy
    )


# =========================
# MESES
# =========================
@app.route("/crear_mes", methods=["POST"])
def crear_mes():
    usuario = session["usuario"]
    datos = cargar_datos(usuario)

    nombre = request.form["nombre"]
    ingreso = float(request.form["ingreso"])

    if nombre in datos["meses"]:
        flash("Ese mes ya existe")
        return redirect(url_for("inicio"))

    if ingreso <= 0:
        flash("El ingreso debe ser mayor que 0")
        return redirect(url_for("inicio"))

    gastos_fijos_mes = [
        {"descripcion": g["descripcion"], "importe": g["importe"]}
        for g in datos["gastos_fijos"]
    ]

    datos["meses"][nombre] = {
        "ingreso": ingreso,
        "gastos_fijos": gastos_fijos_mes,
        "gastos_variables": []
    }

    datos["mes_actual"] = nombre
    guardar_datos(usuario, datos)

    return redirect(url_for("inicio"))


@app.route("/cambiar_mes", methods=["POST"])
def cambiar_mes():
    usuario = session["usuario"]
    datos = cargar_datos(usuario)

    datos["mes_actual"] = request.form["mes"]
    guardar_datos(usuario, datos)

    return redirect(url_for("inicio"))


@app.route("/borrar_mes", methods=["POST"])
def borrar_mes():
    usuario = session["usuario"]
    datos = cargar_datos(usuario)

    mes = datos["mes_actual"]
    if not mes:
        flash("No hay mes para borrar")
        return redirect(url_for("inicio"))

    datos["meses"].pop(mes)
    datos["mes_actual"] = next(iter(datos["meses"]), None)

    guardar_datos(usuario, datos)
    flash(f"Mes '{mes}' borrado")

    return redirect(url_for("inicio"))


# =========================
# GASTOS VARIABLES
# =========================
@app.route("/añadir_gasto_variable", methods=["POST"])
def añadir_gasto_variable():
    usuario = session["usuario"]
    datos = cargar_datos(usuario)

    mes = datos["mes_actual"]
    if not mes:
        flash("No hay mes seleccionado")
        return redirect(url_for("inicio"))

    descripcion = request.form["descripcion"]
    importe = float(request.form["importe"])
    dia = request.form["dia"]
    mes_fecha = request.form["mes"]

    if importe <= 0:
        flash("El importe debe ser mayor que 0")
        return redirect(url_for("inicio"))

    datos["meses"][mes]["gastos_variables"].append({
        "descripcion": descripcion,
        "importe": importe,
        "fecha": f"{dia}/{mes_fecha}"
    })

    guardar_datos(usuario, datos)
    return redirect(url_for("inicio"))


@app.route("/eliminar_gasto_variable/<int:idx>")
def eliminar_gasto_variable(idx):
    usuario = session["usuario"]
    datos = cargar_datos(usuario)

    gastos = datos["meses"][datos["mes_actual"]]["gastos_variables"]

    if idx < 0 or idx >= len(gastos):
        flash("El gasto no existe")
        return redirect(url_for("inicio"))

    gastos.pop(idx)
    guardar_datos(usuario, datos)

    return redirect(url_for("inicio"))


# =========================
# GASTOS FIJOS
# =========================
@app.route("/gastos_fijos")
def ver_gastos_fijos():
    usuario = session["usuario"]
    datos = cargar_datos(usuario)

    return render_template("gastos_fijos.html", gastos_fijos=datos["gastos_fijos"])


@app.route("/añadir_gasto_fijo", methods=["POST"])
def añadir_gasto_fijo():
    usuario = session["usuario"]
    datos = cargar_datos(usuario)

    descripcion = request.form["descripcion"]
    importe = float(request.form["importe"])

    if importe <= 0:
        flash("El importe debe ser mayor que 0")
        return redirect(url_for("ver_gastos_fijos"))

    datos["gastos_fijos"].append({
        "descripcion": descripcion,
        "importe": importe
    })

    if datos["mes_actual"]:
        datos["meses"][datos["mes_actual"]]["gastos_fijos"].append({
            "descripcion": descripcion,
            "importe": importe
        })

    guardar_datos(usuario, datos)
    flash("Gasto fijo añadido")

    return redirect(url_for("ver_gastos_fijos"))


# =========================
# EXPORTAR
# =========================
@app.route("/exportar_csv")
def exportar_csv():
    usuario = session["usuario"]
    datos = cargar_datos(usuario)

    mes = datos["mes_actual"]
    if not mes:
        flash("No hay mes seleccionado")
        return redirect(url_for("inicio"))

    mes_data = datos["meses"][mes]

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha", "Concepto", "Importe", "Tipo"])

    for g in mes_data["gastos_fijos"]:
        writer.writerow(["--/--", g["descripcion"], g["importe"], "Fijo"])

    for g in mes_data["gastos_variables"]:
        writer.writerow([
            g.get("fecha", "--/--"),
            g["descripcion"],
            g["importe"],
            "Variable"
        ])

    output.seek(0)

    return send_file(
        BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{mes}.csv"
    )


# =========================
# ARRANQUE
# =========================
if __name__ == "__main__":
    app.run(debug=True)

