from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os
import json
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.permanent_session_lifetime = timedelta(minutes=30)

# Filtro personalizado para formatar preços
@app.template_filter('format_brl')
def format_brl(value):
    if isinstance(value, (int, float)):
        return f"R$ {value:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")
    return value

# Arquivo para controle de disponibilidade
OPCOES_DISPONIVEIS_FILE = "opcoes_disponiveis.json"

# Cardápio completo original (não modificar estrutura)
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

PEDIDOS_FILE = "pedidos.xlsx"

# Funções de controle de disponibilidade (NOVO)
def carregar_disponibilidade():
    try:
        if os.path.exists(OPCOES_DISPONIVEIS_FILE):
            with open(OPCOES_DISPONIVEIS_FILE, 'r') as f:
                return json.load(f)
        return {str(item['id']): True for item in CARDAPIO_COMPLETO}  # Padrão: todos disponíveis
    except:
        return {str(item['id']): True for item in CARDAPIO_COMPLETO}

def salvar_disponibilidade(disponibilidade):
    with open(OPCOES_DISPONIVEIS_FILE, 'w') as f:
        json.dump(disponibilidade, f)

def get_opcoes_disponiveis():
    disponibilidade = carregar_disponibilidade()
    return [item for item in CARDAPIO_COMPLETO if disponibilidade.get(str(item['id']), True)]

# Funções existentes (não modificar)
def criar_tabela_excel():
    if not os.path.exists(PEDIDOS_FILE):
        df = pd.DataFrame(columns=[
            "Pedido", "Pagamento", "Cidade", "Bairro", 
            "Rua", "Número", "Ponto de Referência", "Valor Total"
        ])
        df.to_excel(PEDIDOS_FILE, index=False, engine="openpyxl")

def formatar_preco(preco):
    return f"R$ {preco:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")

criar_tabela_excel()

# Rotas existentes (modificadas apenas para usar get_opcoes_disponiveis)
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
        opcoes=get_opcoes_disponiveis(),  # Alterado para usar apenas disponíveis
        ingredientes=ingredientes_disponiveis,
        carrinho=session['carrinho']
    )

# Rotas existentes (não modificar)
@app.route('/adicionar_carrinho/<int:id_item>')
def adicionar_carrinho(id_item):
    if 'carrinho' not in session:
        session['carrinho'] = []
    
    item = next((item for item in get_opcoes_disponiveis() if item["id"] == id_item), None)
    if item:
        session['carrinho'].append({"nome": item["nome"], "preco": item["preco"]})
        session.modified = True
    
    return redirect(url_for('opcoes'))

@app.route('/adicionar_personalizado', methods=['POST'])
def adicionar_personalizado():
    if 'carrinho' not in session:
        session['carrinho'] = []
    
    ingredientes = request.form.getlist('ingredientes')
    if ingredientes:
        session['carrinho'].append({
            "nome": "Monte seu prato: " + ", ".join(ingredientes),
            "preco": 20.00
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
    
    itens_formatados = [
        f"{item['nome']} ({formatar_preco(item['preco'])})" 
        for item in session['carrinho']
    ]
    
    valor_total = sum(item['preco'] for item in session['carrinho'])
    
    dados_pedido = {
        "Pedido": " | ".join(itens_formatados),
        "Pagamento": request.form.get("pagamento"),
        "Cidade": request.form.get("cidade"),
        "Bairro": request.form.get("bairro"),
        "Rua": request.form.get("rua"),
        "Número": request.form.get("numero"),
        "Ponto de Referência": request.form.get("ponto_referencia"),
        "Valor Total": valor_total
    }
    
    df = pd.read_excel(PEDIDOS_FILE, engine="openpyxl") if os.path.exists(PEDIDOS_FILE) else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([dados_pedido])], ignore_index=True)
    df.to_excel(PEDIDOS_FILE, index=False, engine="openpyxl")
    
    endereco = f"{dados_pedido['Rua']}, {dados_pedido['Número']}, {dados_pedido['Bairro']}, {dados_pedido['Cidade']}"
    
    session.pop('carrinho', None)
    
    return render_template(
        "confirmacao.html",
        pedido=" | ".join(itens_formatados),
        pagamento=dados_pedido["Pagamento"],
        endereco=endereco,
        referencia=dados_pedido["Ponto de Referência"],
        valor_total=formatar_preco(valor_total)
    )

# Nova rota para gerenciamento (ADICIONADO SEM INTERFERIR NO EXISTENTE)
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