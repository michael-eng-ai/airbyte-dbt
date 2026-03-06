#!/usr/bin/env python3
"""
Script para popular banco de dados com dados fictícios
Usado pelo Airflow para simular dados em produção
"""

import psycopg2
import random
from datetime import datetime, timedelta

# Configurações de conexão
DB_CONFIG = {
    'host': 'postgres_source_db',  # Nome do container no Docker
    'port': 5432,
    'database': 'db_source',
    'user': 'admin',
    'password': 'admin'
}

def conectar_db():
    """Conecta ao banco PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f" Erro ao conectar ao banco: {e}")
        return None

def inserir_dados_ficticios():
    """Insere dados fictícios no banco"""
    conn = conectar_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Inserir alguns clientes
        clientes = [
            ('João Silva', 'joao@email.com'),
            ('Maria Santos', 'maria@email.com'),
            ('Pedro Costa', 'pedro@email.com')
        ]
        
        for nome, email in clientes:
            cur.execute("""
                INSERT INTO public.clientes (nome, email, data_cadastro)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO NOTHING
            """, (nome, email, datetime.now()))
        
        # Inserir alguns pedidos
        produtos = ['Notebook', 'Mouse', 'Teclado', 'Monitor']
        for _ in range(5):
            cur.execute("""
                INSERT INTO public.pedidos (cliente_id, produto, quantidade, preco_unitario, data_pedido)
                SELECT id, %s, %s, %s, %s
                FROM public.clientes
                ORDER BY RANDOM()
                LIMIT 1
            """, (
                random.choice(produtos),
                random.randint(1, 3),
                round(random.uniform(50, 500), 2),
                datetime.now() - timedelta(days=random.randint(0, 30))
            ))
        
        print(" Dados fictícios inseridos com sucesso")
        return True
        
    except Exception as e:
        print(f" Erro ao inserir dados: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print(" Populando banco com dados fictícios...")
    if inserir_dados_ficticios():
        print(" Processo concluído")
    else:
        print(" Processo falhou")