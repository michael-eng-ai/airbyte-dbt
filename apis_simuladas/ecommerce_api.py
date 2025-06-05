#!/usr/bin/env python3
"""
API E-commerce Simulada
Simula um sistema de e-commerce com produtos, vendas e clientes
Para demonstrar CDC e integração multi-fonte
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import pandas as pd
import random
from datetime import datetime, timedelta
from faker import Faker
import time
import threading

app = FastAPI(title="E-commerce API", version="1.0.0")
fake = Faker('pt_BR')

# Base de dados em memória (simula sistema transacional)
produtos_db = []
vendas_db = []
clientes_ecommerce_db = []

# Contadores para IDs
produto_id_counter = 1
venda_id_counter = 1
cliente_id_counter = 1

def gerar_produtos_iniciais():
    """Gera produtos iniciais"""
    global produto_id_counter
    
    categorias = [
        "Eletrônicos", "Roupas", "Casa & Jardim", "Livros", 
        "Esportes", "Beleza", "Automóveis", "Brinquedos"
    ]
    
    for _ in range(50):
        produto = {
            "id": produto_id_counter,
            "nome": fake.catch_phrase(),
            "categoria": random.choice(categorias),
            "preco": round(random.uniform(19.99, 999.99), 2),
            "estoque": random.randint(0, 100),
            "descricao": fake.text(max_nb_chars=200),
            "marca": fake.company(),
            "data_cadastro": fake.date_time_between(start_date='-1y', end_date='now').isoformat(),
            "ativo": random.choice([True, True, True, False])  # 75% ativos
        }
        produtos_db.append(produto)
        produto_id_counter += 1

def gerar_clientes_iniciais():
    """Gera clientes iniciais"""
    global cliente_id_counter
    
    for _ in range(100):
        cliente = {
            "id": cliente_id_counter,
            "nome": fake.name(),
            "email": fake.email(),
            "telefone": fake.phone_number(),
            "cpf": fake.cpf(),
            "data_nascimento": fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
            "endereco": {
                "rua": fake.street_address(),
                "cidade": fake.city(),
                "estado": fake.state_abbr(),
                "cep": fake.postcode()
            },
            "data_cadastro": fake.date_time_between(start_date='-2y', end_date='now').isoformat(),
            "vip": random.choice([True, False]),
            "total_compras": 0,
            "valor_total_gasto": 0.0
        }
        clientes_ecommerce_db.append(cliente)
        cliente_id_counter += 1

def simular_vendas():
    """Simula vendas em tempo real"""
    global venda_id_counter
    
    while True:
        if produtos_db and clientes_ecommerce_db:
            # 70% chance de gerar uma venda a cada ciclo
            if random.random() < 0.7:
                produto = random.choice([p for p in produtos_db if p['ativo']])
                cliente = random.choice(clientes_ecommerce_db)
                quantidade = random.randint(1, 3)
                
                venda = {
                    "id": venda_id_counter,
                    "cliente_id": cliente["id"],
                    "produto_id": produto["id"],
                    "quantidade": quantidade,
                    "preco_unitario": produto["preco"],
                    "valor_total": quantidade * produto["preco"],
                    "desconto": round(random.uniform(0, 0.15), 2) if random.random() < 0.3 else 0,
                    "metodo_pagamento": random.choice(["PIX", "Cartão de Crédito", "Cartão de Débito", "Boleto"]),
                    "status": random.choice(["Pendente", "Processando", "Enviado", "Entregue"]),
                    "data_venda": datetime.now().isoformat(),
                    "canal": random.choice(["Website", "Mobile App", "Marketplace"])
                }
                
                # Aplicar desconto
                if venda["desconto"] > 0:
                    venda["valor_total"] *= (1 - venda["desconto"])
                    venda["valor_total"] = round(venda["valor_total"], 2)
                
                vendas_db.append(venda)
                
                # Atualizar estoque
                produto["estoque"] = max(0, produto["estoque"] - quantidade)
                
                # Atualizar estatísticas do cliente
                cliente["total_compras"] += 1
                cliente["valor_total_gasto"] += venda["valor_total"]
                
                venda_id_counter += 1
                
                print(f"🛒 Nova venda: {venda['id']} - {produto['nome']} - R$ {venda['valor_total']}")
        
        # Aguardar entre 3 a 10 segundos
        time.sleep(random.uniform(3, 10))

@app.on_event("startup")
async def startup_event():
    """Inicialização da API"""
    print("🚀 Iniciando API E-commerce...")
    gerar_produtos_iniciais()
    gerar_clientes_iniciais()
    
    # Iniciar simulador de vendas em thread separada
    simulator_thread = threading.Thread(target=simular_vendas, daemon=True)
    simulator_thread.start()
    
    print("✅ API E-commerce iniciada com sucesso!")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "service": "E-commerce API",
        "version": "1.0.0",
        "endpoints": [
            "/produtos",
            "/vendas", 
            "/clientes",
            "/stats",
            "/health"
        ]
    }

@app.get("/produtos")
async def listar_produtos(limit: int = 100, categoria: str = None):
    """Lista produtos"""
    produtos = produtos_db[:limit]
    
    if categoria:
        produtos = [p for p in produtos if p['categoria'].lower() == categoria.lower()]
    
    return {
        "total": len(produtos),
        "dados": produtos,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/vendas")
async def listar_vendas(limit: int = 100, data_inicio: str = None):
    """Lista vendas"""
    vendas = vendas_db
    
    if data_inicio:
        data_filtro = datetime.fromisoformat(data_inicio)
        vendas = [v for v in vendas if datetime.fromisoformat(v['data_venda']) >= data_filtro]
    
    vendas = vendas[-limit:]  # Últimas vendas
    
    return {
        "total": len(vendas),
        "dados": vendas,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/clientes")
async def listar_clientes(limit: int = 100, vip_only: bool = False):
    """Lista clientes"""
    clientes = clientes_ecommerce_db
    
    if vip_only:
        clientes = [c for c in clientes if c['vip']]
    
    clientes = clientes[:limit]
    
    return {
        "total": len(clientes),
        "dados": clientes,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/stats")
async def estatisticas():
    """Estatísticas do e-commerce"""
    total_vendas = len(vendas_db)
    receita_total = sum(v['valor_total'] for v in vendas_db)
    ticket_medio = receita_total / max(1, total_vendas)
    
    # Vendas por status
    vendas_por_status = {}
    for venda in vendas_db:
        status = venda['status']
        vendas_por_status[status] = vendas_por_status.get(status, 0) + 1
    
    # Top produtos
    vendas_por_produto = {}
    for venda in vendas_db:
        produto_id = venda['produto_id']
        vendas_por_produto[produto_id] = vendas_por_produto.get(produto_id, 0) + venda['quantidade']
    
    return {
        "resumo": {
            "total_vendas": total_vendas,
            "receita_total": round(receita_total, 2),
            "ticket_medio": round(ticket_medio, 2),
            "total_produtos": len(produtos_db),
            "total_clientes": len(clientes_ecommerce_db),
            "clientes_vip": len([c for c in clientes_ecommerce_db if c['vip']])
        },
        "vendas_por_status": vendas_por_status,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🚀 Iniciando API E-commerce na porta 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 