"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Todos
#from models import Person

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace(
        "postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object


@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints


@app.route('/')
def sitemap():
    return generate_sitemap(app)


@app.route('/user', methods=['GET'])
def handle_hello():
    if request.method == "GET":
        users = User.query.all()

        users = list(map(lambda item: item.serialize(), users))
        new_users = []

        for user in users:
            new_users.append(user.get("username"))
    return jsonify(new_users), 200


@app.route("/user/<string:username>", methods=["GET"])
def get_user(username=None):
    if request.method == "GET":
        user = User.query.filter_by(username=username).first()
        if user is None:
            return jsonify({"msg": "user not found"}), 404
        else:
            todos = Todos.query.filter_by(user_id=user.id).all()
            todos = list(map(lambda item: item.serialize(), todos))
            return jsonify(todos), 200


@app.route("/user/<string:username>", methods=["POST"])
def create_user(username=None):
    if request.method == "POST":
        try:
            data = request.json
        except Exception as error:
            return jsonify({"msg": "Debes enviar un array vacío"}), 500

        if type(data) == list and len(data) == 0:
            user = User.query.filter_by(username=username).first()
            if user is not None:
                return jsonify({"msg": "Usuario ya existe"}), 400
            if user is None:
                user = User(username=username)
                db.session.add(user)
                try:
                    db.session.commit()

                    todos = Todos(label="sample task",
                                  done=False, user_id=user.id)
                    db.session.add(todos)
                    db.session.commit()
                    return jsonify([]), 201
                except Exception as error:
                    print(error)
                    return jsonify({"msg": error.args})


@app.route("/user/<string:username>", methods=["PUT"])
def update_task(username=None):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({"msg": "user not found"}), 404

    if user is not None:
        todos = Todos.query.filter_by(user_id=user.id).all()
        for todo in todos:
            db.session.delete(todo)
        db.session.commit()

        data = request.json
        if len(data) > 1:
            for todo in data:

                todo = Todos(label=todo["label"],
                             done=todo["done"], user_id=user.id)
                db.session.add(todo)
            try:
                db.session.commit()
                return jsonify({"msg": f"Se guardaron {len(data)} tareas"}), 201
            except Exception as error:
                db.session.rollback()
                return jsonify({"msg": error.args})


# this only runs if `$ python src/app.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
