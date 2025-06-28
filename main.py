from flask import Flask, render_template, request, redirect, url_for, session
import json, uuid, os
from datetime import timedelta, datetime
from threading import Lock
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId # Importar ObjectId
from bson.errors import InvalidId # Importar InvalidId para tratamento de erro específico

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('KEY', 'chave')
app.permanent_session_lifetime = timedelta(minutes=30)

pedido_lock = Lock()

from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, FileField, BooleanField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename

# CONSERTO AQUI: Definindo o UPLOAD_FOLDER como um caminho absoluto
# Ele sempre apontará para a pasta static/uploads dentro do diretório raiz da sua aplicação.
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # limite 2MB
app.config['WTF_CSRF_ENABLED'] = False  # pode ativar se quiser proteção CSRF

# Para depuração: imprime o caminho onde as imagens serão salvas
print(f"O diretório de upload de imagens está configurado para: {app.config['UPLOAD_FOLDER']}")


class OpcaoForm(FlaskForm):
    # Definindo o label e o placeholder para o campo 'nome'
    nome = StringField('Nome do Prato', validators=[DataRequired()], render_kw={"placeholder": "Nome do prato"})
    # Definindo o label e o placeholder para o campo 'preco'
    preco = DecimalField('Preço', validators=[DataRequired()], render_kw={"placeholder": "0.00"})
    imagem = FileField('Imagem')
    # Definindo o label para o campo 'disponivel'
    disponivel = BooleanField('Disponível')
    submit = SubmitField('Salvar')


# Usuários fixos (pode adaptar para Mongo depois)
USUARIOS = {
    "admin": {"senha": "admin123", "tipo": "admin"},
    "cliente": {"senha": "1234", "tipo": "cliente"}
}

# MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'saneonline')
CLIENT = MongoClient(MONGO_URI)
DB = CLIENT[DB_NAME]

# Coleções
PEDIDOS_LISTA = DB['pedidos']
OPCOES_DISPONIVEIS = DB['opcoes']

@app.template_filter('format_brl')
def format_brl(value):
    if isinstance(value, (int, float)):
        return f"R$ {value:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")
    return value

CARDAPIO_COMPLETO = [
    {"id": 1, "nome": "Feijoada", "preco": 15.00, "imagem": "feijoada.jpg"},
    {"id": 2, "nome": "Churrasco", "preco": 15.00, "imagem": "churrasco.jpg"},
    {"id": 3, "nome": "Macarronada", "preco": 15.00, "imagem": "macarronada.jpg"},
    {"id": 4, "nome": "Moda da Casa", "preco": 13.50, "imagem": "Moda da Casa.png"}
]

ingredientes_disponiveis = [
    "Arroz branco", "Arroz refogado", "Feijão caseiro", "Feijão tropeiro",
    "Feijão preto", "Macarrão", "Salada", "Farofa",
    "Frango assado", "Frango guisado", "Boi assado", "Boi guisado"
]

def inicializar_opcoes():
    # Verifica se já existem opções no banco antes de inserir as opções padrão
    if OPCOES_DISPONIVEIS.count_documents({}) == 0:
        for item in CARDAPIO_COMPLETO:
            # Aqui, para IDs numéricos iniciais, não há problema em usar int.
            # O problema surge quando _id é um ObjectId gerado automaticamente pelo MongoDB.
            OPCOES_DISPONIVEIS.insert_one({"_id": item["id"], **item, "disponivel": True})
    else:
        # Se já existem documentos, garantir que os antigos IDs numéricos sejam preservados
        # e que novos itens (que podem ter ObjectIds) sejam tratados corretamente.
        pass

def carregar_disponibilidade():
    return {str(item['_id']): item['disponivel'] for item in OPCOES_DISPONIVEIS.find({})}

def salvar_disponibilidade(disponibilidade):
    for item_id_str, disponivel in disponibilidade.items():
        # Tenta converter para ObjectId, se falhar, tenta como inteiro
        try:
            query_id = ObjectId(item_id_str)
        except InvalidId: # Se a conversão para ObjectId falhar
            try:
                query_id = int(item_id_str)
            except ValueError:
                # Se não for nem ObjectId válido nem int, imprime um erro e pula
                print(f"Erro: ID inválido encontrado na disponibilidade: {item_id_str}")
                continue # Pula para o próximo item
        
        OPCOES_DISPONIVEIS.update_one({"_id": query_id}, {"$set": {"disponivel": disponivel}})

def get_opcoes_disponiveis():
    return list(OPCOES_DISPONIVEIS.find({"disponivel": True}))

def salvar_pedido(dados):
    with pedido_lock:
        PEDIDOS_LISTA.insert_one(dados)

def obter_proximo_id():
    ultimo = OPCOES_DISPONIVEIS.find_one({"id": {"$exists": True}}, sort=[("id", -1)])
    return (ultimo["id"] + 1) if ultimo else 1

def formatar_preco(preco):
    return f"R$ {preco:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")

inicializar_opcoes()

# ===== LOGIN =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        user = USUARIOS.get(usuario)

        if user and user["senha"] == senha:
            session['usuario'] = usuario
            session['tipo'] = user["tipo"]
            return redirect(url_for('index'))
        return render_template('login.html', erro="Usuário ou senha inválidos.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== ROTAS PRINCIPAIS =====
@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    if 'carrinho' not in session:
        session['carrinho'] = []
    return render_template("index.html", carrinho=session['carrinho'])

@app.route('/opcoes')
def opcoes():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    if 'carrinho' not in session:
        session['carrinho'] = []
    return render_template("opcoes.html", opcoes=list(OPCOES_DISPONIVEIS.find({"disponivel": True})), ingredientes=ingredientes_disponiveis, carrinho=session['carrinho'])


@app.route('/adicionar_carrinho/<id_item>') # ID agora pode ser string (ObjectId ou int)
def adicionar_carrinho(id_item):
    if 'carrinho' not in session:
        session['carrinho'] = []

    # Usar ObjectId para buscar no MongoDB se o ID não for numérico
    try:
        # Primeiro tenta como inteiro
        query_id = int(id_item)
        item = OPCOES_DISPONIVEIS.find_one({"id": query_id, "disponivel": True})
    except ValueError:
        try:
            # Se falhar, tenta como ObjectId
            query_id = ObjectId(id_item)
            item = OPCOES_DISPONIVEIS.find_one({"_id": query_id, "disponivel": True})
        except InvalidId:
            item = None


    if item:
        # Garante que o _id é transformado em string ao adicionar ao carrinho
        item_to_add = {k: v for k, v in item.items()}
        if '_id' in item_to_add:
            item_to_add['_id'] = str(item_to_add['_id']) # Converte ObjectId para string
        session['carrinho'].append(item_to_add)
        session.modified = True
    return redirect(url_for('opcoes'))

@app.route('/adicionar_personalizado', methods=['POST'])
def adicionar_personalizado():
    if 'carrinho' not in session:
        session['carrinho'] = []
    ingredientes = request.form.getlist('ingredientes')
    if ingredientes:
        session['carrinho'].append({
            "id": 999, # Este ID pode ser problemático se usado para buscar no DB futuramente
            "nome": "Monte seu prato: " + ", ".join(ingredientes),
            "preco": 20.00,
            "imagem": "personalizado.jpg"
        })
        session.modified = True
    return redirect(url_for('opcoes'))

@app.route('/remover_item/<int:index>')
def remover_item(index):
    if 'carrinho' in session and 0 <= index < len(session['carrinho']):
        session['carrinho'].pop(index)
        session.modified = True
    return redirect(url_for('opcoes'))

@app.route('/finalizar_pedido')
def finalizar_pedido():
    if 'carrinho' not in session or not session['carrinho']:
        return redirect(url_for('opcoes'))
    itens_formatados = [f"{item['nome']} ({formatar_preco(item['preco'])})" for item in session['carrinho']]
    return render_template("pedido.html", carrinho=session['carrinho'], pedido=" | ".join(itens_formatados), valor_total=formatar_preco(sum(item['preco'] for item in session['carrinho'])))

@app.route('/fazer_pedido', methods=['POST'])
def fazer_pedido():
    if 'carrinho' not in session or not session['carrinho']:
        return redirect(url_for('index'))

    pedido_id = str(uuid.uuid4())[:8].upper()
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    itens_formatados = [f"{item['nome']} ({formatar_preco(item['preco'])})" for item in session['carrinho']]
    valor_total = sum(item['preco'] for item in session['carrinho'])

    dados_pedido = {
        "ID": pedido_id,
        "DataHora": data_hora,
        "Cliente": request.form.get("nome_cliente"),
        "Telefone": request.form.get("telefone"),
        "Pedido": itens_formatados,
        "Pagamento": request.form.get("pagamento"),
        "Cidade": request.form.get("cidade"),
        "Bairro": request.form.get("bairro"),
        "Rua": request.form.get("rua"),
        "Numero": request.form.get("numero"),
        "Referencia": request.form.get("ponto_referencia"),
        "ValorTotal": valor_total,
        "Status": "Recebido"
    }

    salvar_pedido(dados_pedido)
    session.pop('carrinho', None)
    endereco = f"{dados_pedido['Rua']}, {dados_pedido['Numero']}, {dados_pedido['Bairro']}, {dados_pedido['Cidade']}"

    return render_template("confirmacao.html", pedido_id=pedido_id, pedido=" | ".join(itens_formatados), cliente=dados_pedido["Cliente"], telefone=dados_pedido["Telefone"], pagamento=dados_pedido["Pagamento"], endereco=endereco, referencia=dados_pedido["Referencia"], valor_total=formatar_preco(valor_total), data_hora=data_hora)


@app.route('/admin/cardapio', methods=['GET', 'POST'])
def gerenciar_cardapio():
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    form = OpcaoForm()
    opcoes = list(OPCOES_DISPONIVEIS.find({}))

    if form.validate_on_submit():
        data = {
            "nome": form.nome.data,
            "preco": float(form.preco.data),
            "disponivel": bool(form.disponivel.data)
        }
        file = form.imagem.data
        if file:
            filename = secure_filename(file.filename)
            # CONSERTO AQUI: Usando o caminho absoluto para salvar o arquivo
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            data['imagem'] = filename

        if request.args.get('editar'):
            item_id_to_edit = request.args['editar']
            # Tenta converter para ObjectId, se falhar, tenta como inteiro
            try:
                query_id = ObjectId(item_id_to_edit)
            except InvalidId:
                try:
                    query_id = int(item_id_to_edit)
                except ValueError:
                    print(f"Erro: ID inválido encontrado na edição de cardápio: {item_id_to_edit}")
                    return redirect(url_for('gerenciar_cardapio')) # Redireciona para evitar erro

            OPCOES_DISPONIVEIS.update_one({"_id": query_id}, {"$set": data})
        else:
            # Para novos itens, o MongoDB gera automaticamente um ObjectId
            data['id'] = obter_proximo_id()
            OPCOES_DISPONIVEIS.insert_one(data)


        return redirect(url_for('gerenciar_cardapio'))

    # se for edição, carrega dados
    if request.args.get('editar') and request.method == 'GET':
        item_id_to_edit = request.args['editar']
        # Tenta converter para ObjectId, se falhar, tenta como inteiro
        try:
            query_id = ObjectId(item_id_to_edit)
            item = OPCOES_DISPONIVEIS.find_one({"_id": query_id})
        except InvalidId:
            try:
                query_id = int(item_id_to_edit)
                item = OPCOES_DISPONIVEIS.find_one({"_id": query_id})
            except ValueError:
                item = None # ID inválido

        if item: # Certificar-se de que o item foi encontrado
            form.nome.data = item.get('nome')
            form.preco.data = item.get('preco')
            form.disponivel.data = item.get('disponivel', False)

    return render_template('gerenciar_cardapio.html', form=form, opcoes=opcoes)

@app.route('/admin/cardapio/excluir/<item_id>', methods=['POST'])
def excluir_opcao(item_id):
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))
    
    # Tenta converter para ObjectId, se falhar, tenta como inteiro
    try:
        query_id = ObjectId(item_id)
    except InvalidId:
        try:
            query_id = int(item_id)
        except ValueError:
            print(f"Erro: ID inválido encontrado na exclusão de opção: {item_id}")
            return redirect(url_for('gerenciar_cardapio')) # Redireciona para evitar erro

    OPCOES_DISPONIVEIS.delete_one({"_id": query_id})
    return redirect(url_for('gerenciar_cardapio'))

# ===== ADMIN =====
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        disponibilidade = {}
        for item in OPCOES_DISPONIVEIS.find({}):
            item_id = str(item['_id']) # Garante que o ID seja string (ObjectId)
            disponibilidade[item_id] = request.form.get(f'disponivel_{item_id}') == 'on'
        salvar_disponibilidade(disponibilidade)
        return redirect(url_for('admin'))

    opcoes_com_status = [
        {
            "id": str(item['_id']), # Converter _id para string para usar como 'id' no HTML
            "nome": item['nome'],
            "preco": item['preco'],
            "imagem": item.get('imagem', ''), # Usar .get para evitar KeyError se imagem não existir
            "disponivel": item['disponivel']
        }
        for item in OPCOES_DISPONIVEIS.find({})
    ]
    return render_template("admin.html", opcoes=opcoes_com_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
