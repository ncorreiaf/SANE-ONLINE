# 🍽️ Sistema de Pedidos com Flask

Um sistema simples de pedidos de marmitas online desenvolvido com **Flask**, **Pandas** e **MONGODB**, com funcionalidades de cardápio dinâmico, montagem de prato personalizado, carrinho de compras, finalização de pedido e painel administrativo para controle de disponibilidade.

---

## 🚀 Funcionalidades

- Exibição de cardápio com imagens e preços
- Adição de pratos prontos ou personalizados ao carrinho
- Finalização de pedido com formulário completo
- Armazenamento dos pedidos em banco
- Painel administrativo para habilitar/desabilitar itens do cardápio
- Formatação de valores no padrão brasileiro (R$)

---

## 🛠️ Tecnologias Utilizadas

- Python 3
- Flask
- pymongo
- Flask-wtf
- wtforms
- werkzeug
- python-dotenv
- Pandas
- openpyxl
- HTML + Jinja2 Templates
- Bootstrap (frontend)
- JSON + Banco de dados MongoDB

---

## 📦 Instalação para rodar localmente

1. **Clone este repositório:**

```bash
git clone https://github.com/ncorreiaf/SANE-ONLINE.git
cd SANE-ONLINE
```

2. **Instale as dependências do projeto:**
```bash
pip install Flask pymongo python-dotenv pandas openpyxl
pip install  flask-wtf wtforms werkzeug
```

3. **Instale o MongoDB:**

[MongoDB](https://www.mongodb.com/try/download/community)
```bash
Após a instalação, inicialize o software MongoDB Compass.
```

4. **Inicialize o servidor**

Crie uma conexão no MongoDB Compass com as seguintes configurações:
```bash
URI: mongodb://localhost:27017
Name: saneonline
```

5. **Configure as variáveis de ambiente**

Crie um arquivo na pasta raiz do projeto nomeado como *.env* com as seguintes configurações:
```bash
SECRET_KEY='chave'
MONGO_URI='mongodb://localhost:27017/'
DB_NAME='saneonline'
```
Ou
```bash
Pegue o arquivo .env.exemple, pois já tem estes valores, e renomeie como .env
```
Ou
```bash
Pegue suas próprias credenciais no serviço de Database MongoDB Atlas
```

6. **Execute o arquivo main**

```bash
python main.py
```