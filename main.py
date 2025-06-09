from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os
import json
import uuid
from datetime import timedelta
from threading import Lock

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'  # Altere para uma chave secreta forte em produção
app.permanent_session_lifetime = timedelta(minutes=30)

# Lock para operações thread-safe
pedido_lock = Lock()

# Filtro para formatar preços
@app.template_filter('format_brl')
def format_brl(value):
    if isinstance(value, (int, float)):
        return f"R$ {value:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")
    return value

# Arquivos de dados
OPCOES_DISPONIVEIS_FILE = "opcoes_disponiveis.json"
PEDIDOS_FILE = "pedidos.xlsx"

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

# Funções de controle de disponibilidade
def carregar_disponibilidade():
    try:
        if os.path.exists(OPCOES_DISPONIVEIS_FILE):
            with open(OPCOES_DISPONIVEIS_FILE, 'r') as f:
                return json.load(f)
        return {str(item['id']): True for item in CARDAPIO_COMPLETO}
    except:
        return {str(item['id']): True for item in CARDAPIO_COMPLETO}

def salvar_disponibilidade(disponibilidade):
    with open(OPCOES_DISPONIVEIS_FILE, 'w') as f:
        json.dump(disponibilidade, f)

def get_opcoes_disponiveis():
    disponibilidade = carregar_disponibilidade()
    return [item for item in CARDAPIO_COMPLETO if disponibilidade.get(str(item['id']), True)]

# Funções para pedidos
def criar_tabela_excel():
    if not os.path.exists(PEDIDOS_FILE):
        colunas = [
            "ID", "DataHora", "Cliente", "Telefone", "Pedido", 
            "Pagamento", "Cidade", "Bairro", "Rua", "Numero", 
            "Referencia", "ValorTotal", "Status"
        ]
        df = pd.DataFrame(columns=colunas)
        df.to_excel(PEDIDOS_FILE, index=False, engine="openpyxl")

def salvar_pedido(dados):
    with pedido_lock:
        df = pd.read_excel(PEDIDOS_FILE, engine="openpyxl") if os.path.exists(PEDIDOS_FILE) else pd.DataFrame()
        df = pd.concat([df, pd.DataFrame([dados])], ignore_index=True)
        df.to_excel(PEDIDOS_FILE, index=False, engine="openpyxl")

def formatar_preco(preco):
    return f"R$ {preco:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")

# Inicialização
criar_tabela_excel()

# Rotas principais
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
    
    item = next((item for item in get_opcoes_disponiveis() if item["id"] == id_item), None)
    if item:
        session['carrinho'].append({
            "id": item["id"],
            "nome": item["nome"],
            "preco": item["preco"],
            "imagem": item["imagem"]
        })
        session.modified = True
    
    return redirect(url_for('opcoes'))

@app.route('/adicionar_personalizado', methods=['POST'])
def adicionar_personalizado():
    if 'carrinho' not in session:
        session['carrinho'] = []
    
    ingredientes = request.form.getlist('ingredientes')
    if ingredientes:
        session['carrinho'].append({
            "id": 999,  # ID especial para pratos personalizados
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
    
    # Gerar dados únicos do pedido
    pedido_id = str(uuid.uuid4())[:8].upper()
    data_hora = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Formatando itens
    itens_formatados = [f"{item['nome']} ({formatar_preco(item['preco'])})" for item in session['carrinho']]
    valor_total = sum(item['preco'] for item in session['carrinho'])
    
    # Dados completos do pedido
    dados_pedido = {
        "ID": pedido_id,
        "DataHora": data_hora,
        "Cliente": request.form.get("nome_cliente"),
        "Telefone": request.form.get("telefone"),
        "Pedido": " | ".join(itens_formatados),
        "Pagamento": request.form.get("pagamento"),
        "Cidade": request.form.get("cidade"),
        "Bairro": request.form.get("bairro"),
        "Rua": request.form.get("rua"),
        "Numero": request.form.get("numero"),
        "Referencia": request.form.get("ponto_referencia"),
        "ValorTotal": valor_total,
        "Status": "Recebido"
    }
    
    # Salvar de forma thread-safe
    salvar_pedido(dados_pedido)
    
    # Preparar dados para confirmação
    endereco = f"{dados_pedido['Rua']}, {dados_pedido['Numero']}, {dados_pedido['Bairro']}, {dados_pedido['Cidade']}"
    
    # Limpar carrinho
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
