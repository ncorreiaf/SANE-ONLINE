# utilizado apenas para migrar IDs numéricos para ObjectId no MongoDB nao é necessário para o funcionamento do sistema galera!!
# Este script migra IDs numéricos para ObjectId no MongoDB.
# Certifique-se de ter o pymongo e dotenv instalados: 😊
# pip install pymongo python-dotenv

import os
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'saneonline')

CLIENT = MongoClient(MONGO_URI)
DB = CLIENT[DB_NAME]
OPCOES_DISPONIVEIS = DB['opcoes']

print("Iniciando migração de IDs numéricos para ObjectId...")

# Encontrar documentos com _id que são inteiros
# Usamos {"_id": {"$type": "int"}} para buscar IDs que são do tipo inteiro
query = {"_id": {"$type": 16}} # $type: 16 é o código BSON para Integer (32-bit ou 64-bit)

documentos_para_migrar = OPCOES_DISPONIVEIS.find(query)
total_migrados = 0

for doc in documentos_para_migrar:
    old_id = doc['_id']
    
    # Criar um novo ObjectId
    new_id = ObjectId()

    # Inserir o documento com o novo ObjectId, removendo o _id antigo
    # e preservando o campo 'id' se ele existir e você quiser mantê-lo como referência
    doc_copy = doc.copy()
    del doc_copy['_id'] # Remove o _id antigo para que o novo seja atribuído
    
    # Se você quiser manter o ID numérico original em um novo campo (por exemplo, 'old_numerical_id'), faça:
    # doc_copy['old_numerical_id'] = old_id 
    
    # Inserir o documento com o novo ObjectId gerado automaticamente
    # Isso é feito criando um novo documento e depois removendo o antigo
    try:
        OPCOES_DISPONIVEIS.insert_one(doc_copy)
        OPCOES_DISPONIVEIS.delete_one({"_id": old_id})
        print(f"Migrado documento de _id numérico '{old_id}' para novo ObjectId.")
        total_migrados += 1
    except Exception as e:
        print(f"Erro ao migrar documento com _id '{old_id}': {e}")

if total_migrados == 0:
    print("Nenhum documento com _id numérico encontrado para migração. Os IDs já estão unificados ou são ObjectIds.")
else:
    print(f"Migração concluída! {total_migrados} documentos foram atualizados.")

CLIENT.close()
print("Conexão com o MongoDB fechada.")
