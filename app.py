import string
import random
from pathlib import Path
import os
from dotenv import load_dotenv

import docker
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
db = SQLAlchemy(app)
client = docker.from_env()

load_dotenv()
client.login(
    username=os.getenv("DOCKER_USERNAME"),
    password=os.getenv("DOCKER_PASSWORD"),
    registry="ghcr.io"
)

# Password ---------------------------------------------------------------------
password = Path("./data/password")
password.parent.mkdir(parents=True, exist_ok=True)
if not password.exists():
    password.write_text("".join(random.choices(string.ascii_letters + string.digits, k=16)))

password = password.read_text().strip()

# Database ---------------------------------------------------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data/db.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


class Container(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    docker_id = db.Column(db.String(80), unique=True, nullable=False)
    image = db.Column(db.String(80), nullable=False)
    branch = db.Column(db.String(80), nullable=False)


with app.app_context():
    db.create_all()


# Routes -----------------------------------------------------------------------
@app.get("/")
def list_containers():
    containers = Container.query.all()
    return jsonify([{f"{c.image}:{c.branch}": c.docker_id} for c in containers])


@app.post("/")
def create_container():
    data = request.json

    if "password" not in data or data["password"] != password:
        return jsonify({"error": "password is incorrect"}), 401

    if "image" not in data:
        return jsonify({"error": "image is required"}), 400

    if "branch" not in data:
        return jsonify({"error": "branch is required"}), 400

    labels = {
        "traefik.enable": "true",
        f"traefik.http.routers.quizz-{data['image']}-{data['branch']}.tls": "true",
        f"traefik.http.routers.quizz-{data['image']}-{data['branch']}.rule": f"Host(`{data['branch']}.quizz.ozeliurs.com`)",
        f"traefik.http.routers.quizz-{data['image']}-{data['branch']}.entrypoints": "websecure",
        f"traefik.http.routers.quizz-{data['image']}-{data['branch']}.tls.certresolver": "cloudflare",
    }

    container = client.containers.run(
        f"ghcr.io/2019-2020-ps6/2022-2023-ps6-webonjour/{data['image']}:{data['branch']}",
        detach=True,
        labels=labels,
        name=f"quizz-{data['image']}-{data['branch']}",
        network="traefik",
        remove=True
    )

    container = Container(
        docker_id=container.id,
        image=data["image"],
        branch=data["branch"]
    )
    db.session.add(container)
    db.session.commit()

    return jsonify({"id": container.id})


if __name__ == "__main__":
    app.run()
