# 🍽️ Sistema de Pedidos com Flask

Um sistema simples de pedidos de marmitas online desenvolvido com **Flask**, **Pandas** e **Excel**, com funcionalidades de cardápio dinâmico, montagem de prato personalizado, carrinho de compras, finalização de pedido e painel administrativo para controle de disponibilidade.

---

## 🚀 Funcionalidades

- Exibição de cardápio com imagens e preços
- Adição de pratos prontos ou personalizados ao carrinho
- Finalização de pedido com formulário completo
- Armazenamento dos pedidos em arquivo Excel (`pedidos.xlsx`)
- Painel administrativo para habilitar/desabilitar itens do cardápio
- Formatação de valores no padrão brasileiro (R$)

---

## 🛠️ Tecnologias Utilizadas

- Python 3
- Flask
- Pandas
- openpyxl
- HTML + Jinja2 Templates
- Bootstrap (frontend)
- JSON + Excel como "banco de dados" leve

---

## 📦 Instalação

1. **Clone este repositório:**

```bash
git clone https://github.com/ncorreiaf/SANE-ONLINE.git
cd SANE-ONLINE
```

2. **Dependências Python:**
```bash
pip install Flask pymongo python-dotenv pandas openpyxl
```

3. **Instale o MongoDB:**

[MongoDB](https://www.mongodb.com/try/download/community)

4. **Inicialize o servidor**
```bash
mongod --dbpath /caminho/para/seus/dados/db
```

5. **Execute o arquivo main**
```bash
python main.py
```
