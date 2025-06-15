from flask import Flask, render_template, request, redirect, url_for, session
import json
import uuid
from datetime import timedelta, datetime
from threading import Lock
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('KEY', 'chave')
app.permanent_session_lifetime = timedelta(minutes=30)

pedido_lock = Lock()

# MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'saneonline')
CLIENT = MongoClient(MONGO_URI)
DB = CLIENT[DB_NAME]

# Coleções
PEDIDOS_LISTA = DB['pedidos']
OPCOES_DISPONIVEIS = DB['opcoes']

# Preços
@app.template_filter('format_brl')
def format_brl(value):
    if isinstance(value, (int, float)):
        return f"R$ {value:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")
    return value

# Cardápio completo
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

# Funções de controle de disponibilidade com MongoDB
def inicializar_opcoes():
    if OPCOES_DISPONIVEIS.count_documents({}) == 0:
        for item in CARDAPIO_COMPLETO:
            OPCOES_DISPONIVEIS.insert_one({"_id": item["id"], **item, "disponivel": True})
    
def carregar_disponibilidade():
    opcoes = OPCOES_DISPONIVEIS.find({})
    return {str(item['_id']): item['disponivel'] for item in opcoes}

def salvar_disponibilidade(disponibilidade):
    for item_id, disponivel in disponibilidade.items():
        OPCOES_DISPONIVEIS.update_one({"_id": int(item_id)}, {"$set": {"disponivel": disponivel}})

def get_opcoes_disponiveis():
    return list(OPCOES_DISPONIVEIS.find({"disponivel": True}))

# Pedidos no MDB
def salvar_pedido(dados):
    with pedido_lock:
        PEDIDOS_LISTA.insert_one(dados)

def formatar_preco(preco):
    return f"R$ {preco:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")

# Inicialização
inicializar_opcoes()

# Rotas
@app.route('/')
def index():
    if 'carrinho' not in session:
        session['carrinho'] = []
    return render_template("index.html", carrinho=session['carrinho'])

@app.route('/opcoes')
def opcoes():
    if 'carrinho' not in session:
        session['carrinho'] = []
    return render_template(
        "opcoes.html",
        opcoes=get_opcoes_disponiveis(),
        ingredientes=ingredientes_disponiveis,
        carrinho=session['carrinho']
    )

@app.route('/adicionar_carrinho/<int:id_item>')
def adicionar_carrinho(id_item):
    if 'carrinho' not in session:
        session['carrinho'] = []
    
    # Busca item
    item = OPCOES_DISPONIVEIS.find_one({"_id": id_item, "disponivel": True})
    if item:
        item_para_carrinho = {k: v for k, v in item.items() if k != '_id'}
        session['carrinho'].append(item_para_carrinho)
        session.modified = True
    
    return redirect(url_for('opcoes'))

@app.route('/adicionar_personalizado', methods=['POST'])
def adicionar_personalizado():
    if 'carrinho' not in session:
        session['carrinho'] = []
    
    ingredientes = request.form.getlist('ingredientes')
    if ingredientes:
        session['carrinho'].append({
            "id": 999,
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
    if 'carrinho' not in session or len(session['carrinho']) == 0:
        return redirect(url_for('opcoes'))
    
    itens_formatados = [
        f"{item['nome']} ({formatar_preco(item['preco'])})"
        for item in session['carrinho']
    ]
    
    return render_template(
        "pedido.html",
        carrinho=session['carrinho'],
        pedido=" | ".join(itens_formatados),
        valor_total=formatar_preco(sum(item['preco'] for item in session['carrinho']))
    )

@app.route('/fazer_pedido', methods=['POST'])
def fazer_pedido():
    if 'carrinho' not in session or len(session['carrinho']) == 0:
        return redirect(url_for('index'))
    
    # Dados únicos
    pedido_id = str(uuid.uuid4())[:8].upper()
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Data

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

    endereco = f"{dados_pedido['Rua']}, {dados_pedido['Numero']}, {dados_pedido['Bairro']}, {dados_pedido['Cidade']}"

    session.pop('carrinho', None)
    
    return render_template(
        "confirmacao.html",
        pedido_id=pedido_id,
        pedido=" | ".join(itens_formatados),
        cliente=dados_pedido["Cliente"],
        telefone=dados_pedido["Telefone"],
        pagamento=dados_pedido["Pagamento"],
        endereco=endereco,
        referencia=dados_pedido["Referencia"],
        valor_total=formatar_preco(valor_total),
        data_hora=data_hora
    )

# Painel Admin
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        disponibilidade = {}
        for item in CARDAPIO_COMPLETO:
            disponibilidade[str(item['id'])] = request.form.get(f'disponivel_{item["id"]}') == 'on'
        salvar_disponibilidade(disponibilidade)
        return redirect(url_for('admin'))
    
    disponibilidade = carregar_disponibilidade()
    opcoes_com_status = []
    for item in CARDAPIO_COMPLETO:
        opcoes_com_status.append({
            **item,
            "disponivel": disponibilidade.get(str(item['id']), True)
        })
    
    return render_template("admin.html", opcoes=opcoes_com_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
