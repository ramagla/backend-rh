from flask import request, jsonify
from flask_jwt_extended import create_access_token

# Simulação de banco de dados de usuários
users_db = {
    "admin": {"password": "1234", "role": "admin"},
    "operador": {"password": "5678", "role": "operador"},
}

def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = users_db.get(username)
    if not user or user['password'] != password:
        return jsonify({"message": "Usuário ou senha incorretos"}), 401

    access_token = create_access_token(identity={"username": username, "role": user['role']})
    return jsonify(access_token=access_token), 200
