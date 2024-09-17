from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
import os
import pandas as pd
import zipfile
from utils.email_utils import enviar_email_com_anexo

holerite_bp = Blueprint('holerite', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@holerite_bp.route('/enviar-holerites', methods=['POST'])
@jwt_required()
def enviar_holerites():
    if 'excel' not in request.files or 'zip' not in request.files:
        return jsonify({"message": "Arquivos Excel e ZIP são obrigatórios."}), 400

    excel_file = request.files['excel']
    zip_file = request.files['zip']

    # Carrega o arquivo Excel
    df = pd.read_excel(excel_file)
    funcionarios = df[['Nome', 'Email']].to_dict(orient='records')

    # Salva e descompacta o arquivo ZIP
    zip_path = os.path.join(UPLOAD_FOLDER, zip_file.filename)
    zip_file.save(zip_path)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(UPLOAD_FOLDER)

    # Envia os holerites por e-mail
    for funcionario in funcionarios:
        nome = funcionario['Nome']
        email = funcionario['Email']
        holerite_path = os.path.join(UPLOAD_FOLDER, f"{nome}.pdf")

        if os.path.exists(holerite_path):
            assunto = f"Holerite de {nome}"
            corpo = f"Olá {nome},\nSegue em anexo o seu holerite."
            enviar_email_com_anexo(email, assunto, corpo, holerite_path)
        else:
            print(f"Holerite não encontrado para {nome}")

    return jsonify({"message": "Envio de holerites completo."}), 200
