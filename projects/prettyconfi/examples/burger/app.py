#!/usr/bin/env python3
"""Burger Builder Web UI — prettyconfi Flask demo."""

import json
from pathlib import Path

from flask import Flask, render_template, request, jsonify

from prettyconfi import load_schema, compose, WebRunner, to_env, from_env

app = Flask(__name__)

SCHEMA_PATH = Path(__file__).parent / "schema.toml"
SAVE_PATH = Path(__file__).parent / "burger_order.env"


def get_composed():
    schema = load_schema(SCHEMA_PATH)
    return compose([schema])


@app.route("/")
def index():
    composed = get_composed()
    json_schema = WebRunner.to_json_schema(composed)

    # Load saved data if exists
    saved = {}
    if SAVE_PATH.exists():
        saved = from_env(SAVE_PATH)

    return render_template(
        "index.html",
        schema=json.dumps(json_schema),
        saved=json.dumps(saved),
    )


@app.route("/api/validate", methods=["POST"])
def validate():
    data = request.json
    composed = get_composed()
    validated, errors = WebRunner.validate(composed, data)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    return jsonify({"ok": True, "data": validated})


@app.route("/api/save", methods=["POST"])
def save():
    data = request.json
    composed = get_composed()
    validated, errors = WebRunner.validate(composed, data)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    to_env(validated, SAVE_PATH)
    return jsonify({"ok": True, "message": "Order saved!"})


@app.route("/api/submit", methods=["POST"])
def submit():
    data = request.json
    composed = get_composed()
    validated, errors = WebRunner.validate(composed, data)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    to_env(validated, SAVE_PATH)
    return jsonify({"ok": True, "data": validated})


if __name__ == "__main__":
    app.run(debug=True, port=5050)
