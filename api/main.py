from flask import Flask, request, jsonify, send_file, make_response, send_from_directory
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from utils.email_utils import enviar_email_com_anexo
from flask import jsonify
from PyPDF2 import PdfReader, PdfWriter
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import zipfile
import io
import pdfplumber
import re
import pandas as pd
import json
import os



app = Flask(__name__)


# Configuração correta do CORS para permitir requisições do frontend
CORS(app, resources={r"/api/*": {"origins": "https://sistema-rh.azurewebsites.net"}}, supports_credentials=True)


# Configuração da chave secreta para o JWT
app.config['JWT_SECRET_KEY'] = 'sua_chave_secreta'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(minutes=30)
jwt = JWTManager(app)

# Manipulador de requisições OPTIONS global
@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
        return response

# Simulação de banco de dados de usuários
users_db = {
    "admin": {"password": "1234", "role": "admin"},
    "operador": {"password": "5678", "role": "operador"},
}

# Obtém o diretório base onde o script está sendo executado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Caminho do arquivo de log para auditoria
LOG_FILE_PATH = os.path.join(BASE_DIR, 'logs', 'auditoria.txt')

# Caminho para armazenar arquivos temporários
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Função para gravar logs de auditoria no arquivo
def registrar_auditoria(acao, usuario, resultado):
    if not os.path.exists(os.path.join(BASE_DIR, 'logs')):
        os.makedirs(os.path.join(BASE_DIR, 'logs'))
    
    with open(LOG_FILE_PATH, 'a') as log_file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Salvando o log com dados diretos
        log_file.write(f"{timestamp} - {usuario['username']} - {usuario.get('email', 'email@exemplo.com')} - {acao} - Resultado: {resultado}\n")




# Função para enviar notificação por e-mail em caso de erro
def enviar_email_notificacao(email_destinatario, motivo_erro):
    remetente = "seu_email@gmail.com"
    senha = "sua_senha"
    assunto = "Erro no Envio de Holerite"
    
    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = email_destinatario
    msg['Subject'] = assunto

    corpo = f"Houve um erro no envio do holerite: {motivo_erro}"
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remetente, senha)
        servidor.sendmail(remetente, email_destinatario, msg.as_string())
        servidor.quit()
        print(f"E-mail enviado para {email_destinatario}")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {str(e)}")

# Rota para login e geração de token JWT
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Simulação de banco de dados
    user = users_db.get(username)
    if not user or user['password'] != password:
        return jsonify({"message": "Usuário ou senha incorretos"}), 401

    # Geração do token JWT
    access_token = create_access_token(identity={"username": username, "role": user['role']})
    return jsonify(access_token=access_token), 200



# Função para dividir um PDF em várias páginas
def dividir_pdf_em_paginas(pdf_file_path):
    reader = PdfReader(pdf_file_path)
    num_paginas = len(reader.pages)
    
    paginas_separadas = []

    for i in range(num_paginas):
        writer = PdfWriter()
        writer.add_page(reader.pages[i])

        output_filename = f"{UPLOAD_FOLDER}/pagina_{i+1}.pdf"
        with open(output_filename, "wb") as output_pdf:
            writer.write(output_pdf)
            paginas_separadas.append(output_filename)
            print(f"Arquivo salvo: {output_filename}")

    return paginas_separadas

# Função para extrair o nome do funcionário de um PDF
def extrair_nome_do_pdf(caminho_pdf):
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            texto = ""
            for pagina in pdf.pages:
                texto += pagina.extract_text()

            # Procurar a linha que contém "Nome do Funcionário"
            padrao_nome = re.compile(r'Código\s+Nome do Funcionário\s+CBO\s+Departamento\s+Filial.*\n(\d+\s+([A-Za-z\s]+))')
            resultado = padrao_nome.search(texto)

            if resultado:
                nome = resultado.group(2).strip()
                print(f"Nome encontrado: {nome}")
                return nome
            else:
                print(f"Nome não encontrado no arquivo: {caminho_pdf}")
    except Exception as e:
        print(f"Erro ao processar {caminho_pdf}: {e}")
    return None

# Função para renomear os arquivos com base no nome do funcionário
def renomear_com_funcionarios(arquivos_paginas):
    novos_nomes = []
    for arquivo in arquivos_paginas:
        nome_funcionario = extrair_nome_do_pdf(arquivo)

        if nome_funcionario:
            novo_nome = f"{nome_funcionario}.pdf"
            print(f"Renomeando {arquivo} para {novo_nome}")
        else:
            novo_nome = os.path.basename(arquivo)
            print(f"Nome do funcionário não encontrado. Mantendo nome original: {novo_nome}")
        novos_nomes.append(novo_nome)
    return novos_nomes

# Função para renomear e zipar arquivos
def renomear_e_zipar(arquivos, novos_nomes):
    zip_buffer = io.BytesIO()  # Cria um buffer para o arquivo zip

    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for i, arquivo in enumerate(arquivos):
            novo_nome = novos_nomes[i]
            zip_file.write(arquivo, novo_nome)

    zip_buffer.seek(0)  # Volta ao início do buffer para permitir o download
    return zip_buffer

# Rota para dividir, renomear com nomes de funcionários e zipar PDFs
@app.route('/api/dividir-renomear-zipar-pdf', methods=['POST'])
@jwt_required()
def dividir_renomear_zipar_funcionarios():
    if 'file' not in request.files:
        return jsonify({"message": "Nenhum arquivo PDF enviado"}), 400

    pdf_file = request.files['file']

    if pdf_file.filename == '':
        return jsonify({"message": "Nenhum arquivo PDF selecionado"}), 400

    if pdf_file and pdf_file.filename.endswith('.pdf'):
        file_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
        pdf_file.save(file_path)

        # Divide o PDF em várias páginas
        arquivos_paginas = dividir_pdf_em_paginas(file_path)

        # Renomeia os arquivos com base no nome dos funcionários
        novos_nomes = renomear_com_funcionarios(arquivos_paginas)

        # Zipar os arquivos renomeados
        zip_buffer = renomear_e_zipar(arquivos_paginas, novos_nomes)

        # Remove os arquivos temporários
        for arquivo in arquivos_paginas:
            os.remove(arquivo)
        os.remove(file_path)  # Remove o arquivo PDF original

        # Retorna o arquivo zip para download
        return send_file(zip_buffer, as_attachment=True, download_name='arquivos_renomeados_funcionarios.zip', mimetype='application/zip')

    return jsonify({"message": "Formato de arquivo inválido"}), 400


# Rota de teste para extrair o nome do funcionário de um PDF
@app.route('/api/test-extract', methods=['POST'])
def test_extraction():
    if 'file' not in request.files:
        return jsonify({"message": "Nenhum arquivo PDF enviado"}), 400

    pdf_file = request.files['file']
    if pdf_file.filename == '':
        return jsonify({"message": "Nenhum arquivo PDF selecionado"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
    pdf_file.save(file_path)

    nome_funcionario = extrair_nome_do_pdf(file_path)
    if nome_funcionario:
        return jsonify({"message": f"Nome extraído: {nome_funcionario}"}), 200
    else:
        return jsonify({"message": "Nome não encontrado"}), 400
    

def processar_zip_e_enviar_emails(zip_file_path, funcionarios):
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(UPLOAD_FOLDER)

        for funcionario in funcionarios:
            nome_funcionario = funcionario['name']
            email_funcionario = funcionario['email']
            pdf_file_path = os.path.join(UPLOAD_FOLDER, f"{nome_funcionario}.pdf")

            if os.path.exists(pdf_file_path):
                assunto = f"Holerite de {nome_funcionario}"

                # Corpo do e-mail em HTML personalizado
                corpo_html = f"""
                <html>
                <body>
                    <div style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px;">
                        <h2 style="color: #6c757d;">Seu holerite está disponível</h2>
                        <p>Olá, {nome_funcionario}!</p>
                        <p>Seu holerite foi gerado com sucesso! Veja as informações abaixo:</p>
                        <div style="border: 1px solid #dee2e6; padding: 15px; background-color: white;">
                            <p><strong>Empregador:</strong> Bras-Mol Molas e Estampados Ltda</p>
                            <p><strong>Colaborador:</strong> {nome_funcionario}</p>
                            <p><strong>Data de Registro:</strong> {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                        </div>
                        <p>O holerite está anexo neste e-mail.</p>
                        <p style="color: #6c757d;">Obrigado,</p>
                        <p><strong>Bras-Mol Molas e Estampados Ltda</strong></p>
                    </div>
                </body>
                </html>
                """
                
                try:
                    # Enviar e-mail com anexo e corpo em HTML
                    enviar_email_com_anexo(email_funcionario, assunto, corpo_html, pdf_file_path)
                    
                    # Salvar sucesso no arquivo de texto
                    salvar_relatorio_txt(nome_funcionario, email_funcionario, True)
                    print(f"E-mail enviado para {email_funcionario} com o arquivo {pdf_file_path}")
                except Exception as e:
                    # Salvar falha no arquivo de texto
                    salvar_relatorio_txt(nome_funcionario, email_funcionario, False, str(e))
                    print(f"Erro ao enviar e-mail para {email_funcionario}: {e}")
            else:
                print(f"Arquivo PDF não encontrado para {nome_funcionario}.")
    except Exception as e:
        print(f"Erro ao processar ZIP ou enviar e-mails: {e}")
        raise
  


# Função para ler o arquivo Excel e retornar os dados como uma lista de dicionários
def ler_excel(excel_file_path):
    try:
        # Verificar se o arquivo Excel foi salvo corretamente
        if not os.path.exists(excel_file_path):
            print(f"Arquivo Excel não encontrado: {excel_file_path}")
            return None
        
        print(f"Lendo o arquivo Excel: {excel_file_path}")
        df = pd.read_excel(excel_file_path)
        
        # Verifica o conteúdo das colunas e das primeiras linhas
        print("Colunas encontradas no Excel:", df.columns)
        print("Primeiras linhas do Excel:")
        print(df.head())
        
        # Converte as colunas para letras minúsculas
        df.columns = [col.lower() for col in df.columns]
        
        # Verifique se o DataFrame está vazio
        if df.empty:
            print("O arquivo Excel está vazio ou não contém os dados esperados.")
            return None
        
        # Verifique se as colunas 'name' e 'email' existem
        if 'name' not in df.columns or 'email' not in df.columns:
            print("O arquivo Excel não contém as colunas necessárias 'name' e 'email'.")
            return None

        # Transformar o DataFrame em uma lista de dicionários
        funcionarios = df.to_dict(orient='records')
        print(f"Funcionários extraídos: {funcionarios}")
        return funcionarios
    except Exception as e:
        print(f"Erro ao ler o arquivo Excel: {e}")
        return None
    
@app.route('/api/configuracoes', methods=['POST'])
@jwt_required()
def salvar_configuracoes():
    data = request.json

    # Valide e salve as configurações
    smtp_host = data.get('smtpHost')
    smtp_port = data.get('smtpPort')
    smtp_user = data.get('smtpUser')
    smtp_password = data.get('smtpPassword')
    file_path = data.get('filePath')

    # Aqui, você pode salvar essas configurações em um arquivo ou banco de dados
    try:
        with open('configuracoes.json', 'w') as config_file:
            configuracoes = {
                "smtpHost": smtp_host,
                "smtpPort": smtp_port,
                "smtpUser": smtp_user,
                "smtpPassword": smtp_password,
                "filePath": file_path
            }
            json.dump(configuracoes, config_file)

        return jsonify({"message": "Configurações salvas com sucesso!"}), 200
    except Exception as e:
        return jsonify({"message": f"Erro ao salvar configurações: {str(e)}"}), 500

import pdfplumber
import re

# Função para extrair o mês e ano do holerite a partir do PDF
def extrair_mes_ano_holerite(caminho_pdf):
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()

                # Regex para encontrar o mês e ano no holerite
                padrao = re.search(r'Folha\s+Mensal\s+(Mensalista|Horista)\s+([A-Za-zçÇ]+)\s+de\s+(\d{4})', texto, re.DOTALL)
                if padrao:
                    tipo_funcionario = padrao.group(1)  # Mensalista ou Horista
                    mes = padrao.group(2)
                    ano = padrao.group(3)
                    return f"{mes} de {ano} ({tipo_funcionario})"

        return None
    except Exception as e:
        print(f"Erro ao extrair mês e ano do PDF {caminho_pdf}: {str(e)}")
        return None


# Rota para envio de holerites e registro de auditoria
@app.route('/api/enviar-holerites', methods=['POST'])
@jwt_required()
def enviar_holerites():
    usuario = get_jwt_identity()  # Obtém o usuário autenticado
    erros_envio = []  # Lista para armazenar logs de erro
    
    # Verificar se os arquivos foram enviados
    if 'zipfile' not in request.files or 'excelfile' not in request.files:
        registrar_auditoria("Envio de Holerites", usuario, "Erro: Faltam arquivos")
        return jsonify({"message": "Ambos os arquivos são necessários."}), 400

    zip_file = request.files['zipfile']
    excel_file = request.files['excelfile']

    # Salvar os arquivos recebidos
    zip_file_path = os.path.join(UPLOAD_FOLDER, zip_file.filename)
    excel_file_path = os.path.join(UPLOAD_FOLDER, excel_file.filename)

    zip_file.save(zip_file_path)
    excel_file.save(excel_file_path)

    # Ler o Excel e processar o envio de e-mails
    try:
        funcionarios = ler_excel(excel_file_path)
        if funcionarios is None:
            registrar_auditoria("Envio de Holerites", usuario, "Erro: Arquivo Excel inválido")
            return jsonify({"message": "Erro ao processar o arquivo Excel. Verifique se o arquivo contém os dados corretos."}), 400

        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(UPLOAD_FOLDER)

        # Iterar sobre os funcionários
        for funcionario in funcionarios:
            nome_funcionario = funcionario['name']
            email_funcionario = funcionario['email']
            pdf_file_path = os.path.join(UPLOAD_FOLDER, f"{nome_funcionario}.pdf")

            if os.path.exists(pdf_file_path):
                # Extrair a data de referência diretamente do PDF
                data_referencia = extrair_mes_ano_holerite(pdf_file_path)
                if not data_referencia:
                    erros_envio.append(f"Erro: Não foi possível extrair a data do holerite para {nome_funcionario}.")
                    continue  # Pula para o próximo funcionário se não conseguir extrair a data

                assunto = f"Holerite referente a {data_referencia}"

                # Corpo do e-mail em HTML personalizado
                corpo_html = f"""
                <html>
                <body>
                    <div style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px;">
                        <h2 style="color: #6c757d;">Seu holerite está disponível</h2>
                        <p>Olá, {nome_funcionario}!</p>
                        <p>Seu holerite referente a <strong>{data_referencia}</strong> foi gerado com sucesso.</p>
                        <p>O holerite está anexo neste e-mail.</p>
                        <p style="color: #6c757d;">Obrigado,</p>
                        <p><strong>Bras-Mol Molas e Estampados Ltda</strong></p>
                    </div>
                </body>
                </html>
                """

                try:
                    # Enviar e-mail com anexo e corpo em HTML
                    enviar_email_com_anexo(email_funcionario, assunto, corpo_html, pdf_file_path)
                    salvar_relatorio_txt(nome_funcionario, email_funcionario, True)
                    print(f"E-mail enviado para {email_funcionario} com o arquivo {pdf_file_path}")
                except Exception as e:
                    erros_envio.append(f"Erro ao enviar e-mail para {nome_funcionario}: {str(e)}")
                    salvar_relatorio_txt(nome_funcionario, email_funcionario, False, str(e))
            else:
                erros_envio.append(f"Erro: Arquivo PDF não encontrado para {nome_funcionario}.")

        registrar_auditoria("Envio de Holerites", usuario, "Sucesso")
    except Exception as e:
        registrar_auditoria("Envio de Holerites", usuario, f"Erro: {str(e)}")
        return jsonify({"message": f"Erro ao processar arquivos: {str(e)}", "errors": erros_envio}), 500

    # Limpar arquivos temporários
    os.remove(zip_file_path)
    os.remove(excel_file_path)

    return jsonify({"message": "Holerites enviados com sucesso!", "errors": erros_envio}), 200



@app.route('/api/relatorios', methods=['GET'])
@jwt_required()
def obter_relatorios():
    try:
        logs = []
        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, 'r') as log_file:
                for line in log_file:
                    print(f"Processando linha do log: {line.strip()}")  # Log para verificar cada linha processada
                    try:
                        # Regex atualizado para capturar os campos do log corretamente
                        match = re.match(r'^(.*?) - \{\'username\': \'(.*?)\', \'role\': \'(.*?)\'\}: (.*?) - Resultado: (.*)$', line.strip())
                        if match:
                            timestamp, username, role, acao, resultado = match.groups()
                            print(f"Match encontrado: {match.groups()}")  # Verificação de match encontrado
                            logs.append({
                                'timestamp': timestamp,
                                'nome': username,
                                'email': f'{username}@exemplo.com',  # E-mail derivado do nome de usuário
                                'status': resultado
                            })
                        else:
                            print(f"Regex não bateu com a linha: {line.strip()}")
                    except Exception as e:
                        print(f"Erro ao processar linha do log: {line.strip()} - Erro: {str(e)}")
        else:
            print(f"Arquivo de log {LOG_FILE_PATH} não encontrado.")
        print(f"Logs capturados: {logs}")
        return jsonify(logs), 200
    except Exception as e:
        return jsonify({"message": f"Erro ao ler logs: {str(e)}"}), 500


   

def salvar_relatorio_txt(nome, email, success, error_reason=None):
    # Caminho onde o log será salvo
    log_file = os.path.join(UPLOAD_FOLDER, 'relatorios_envio.txt')

    # Formatar o conteúdo do log
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "Sucesso" if success else f"Erro: {error_reason}"
    log_entry = f"{timestamp} | {nome} | {email} | {status}\n"

    # Escrever no arquivo de log
    with open(log_file, 'a') as file:
        file.write(log_entry)


# Rota para buscar logs de auditoria
@app.route('/api/logs', methods=['GET'])
@jwt_required()  # Certifique-se de que o usuário está autenticado
def obter_logs():
    try:
        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, 'r') as log_file:
                logs = log_file.readlines()  # Lê todas as linhas do arquivo de log
            return jsonify(logs), 200  # Retorna os logs em formato JSON
        else:
            return jsonify([]), 200  # Retorna um array vazio se o arquivo não existir
    except Exception as e:
        return jsonify({"message": f"Erro ao ler logs: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(debug=True, host='0.0.0.0', port=port)

for rule in app.url_map.iter_rules():
   print(f"{rule} -> {rule.endpoint}")
