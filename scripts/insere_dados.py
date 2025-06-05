#!/usr/bin/env python3
"""
Script para inserir dados continuamente no PostgreSQL
Simula um ambiente real para demonstrar CDC e pipeline em tempo real
"""

import psycopg2
import random
import time
from datetime import datetime, timedelta
import sys

# Configurações de conexão
DB_CONFIG = {
    'host': 'localhost',
    'port': 5430,
    'database': 'db_source',
    'user': 'admin',
    'password': 'admin'
}

# Dados para geração aleatória
NOMES = [
    'Ana Silva', 'Bruno Costa', 'Carla Santos', 'Diego Almeida', 'Elena Ferreira',
    'Felipe Lima', 'Gabriela Rocha', 'Henrique Souza', 'Isabela Martins', 'João Oliveira',
    'Kamila Pereira', 'Lucas Barbosa', 'Marina Gomes', 'Nicolas Cardoso', 'Olívia Mendes',
    'Pedro Ribeiro', 'Quintina Araújo', 'Rafael Torres', 'Sofia Nascimento', 'Thiago Ramos'
]

PRODUTOS = [
    'Notebook Dell', 'Mouse Logitech', 'Teclado Mecânico', 'Monitor 24"', 'Webcam HD',
    'Smartphone Samsung', 'Tablet iPad', 'Fone Bluetooth', 'Carregador Wireless', 'Cabo USB-C',
    'SSD 1TB', 'Memória RAM 16GB', 'Placa de Vídeo', 'Processador Intel', 'Motherboard ASUS'
]

DOMINIOS_EMAIL = ['gmail.com', 'hotmail.com', 'yahoo.com.br', 'empresa.com', 'outlook.com']

def conectar_db():
    """Conecta ao banco PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return None

def gerar_email(nome):
    """Gera um email baseado no nome"""
    nome_limpo = nome.lower().replace(' ', '.').replace('ã', 'a').replace('é', 'e').replace('í', 'i')
    dominio = random.choice(DOMINIOS_EMAIL)
    numero = random.randint(1, 999)
    return f"{nome_limpo}{numero}@{dominio}"

def inserir_cliente(conn):
    """Insere um novo cliente"""
    try:
        nome = random.choice(NOMES)
        email = gerar_email(nome)
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO public.clientes (nome, email, data_cadastro)
            VALUES (%s, %s, %s)
            RETURNING id;
        """, (nome, email, datetime.now()))
        
        cliente_id = cur.fetchone()[0]
        print(f"➕ Cliente inserido: ID {cliente_id} - {nome} ({email})")
        return cliente_id
        
    except Exception as e:
        print(f"❌ Erro ao inserir cliente: {e}")
        return None

def inserir_pedido(conn, cliente_id=None):
    """Insere um novo pedido"""
    try:
        # Se não foi especificado cliente, pega um aleatório existente
        if cliente_id is None:
            cur = conn.cursor()
            cur.execute("SELECT id FROM public.clientes ORDER BY RANDOM() LIMIT 1")
            result = cur.fetchone()
            if not result:
                print("❌ Nenhum cliente disponível para pedido")
                return None
            cliente_id = result[0]
        
        produto = random.choice(PRODUTOS)
        quantidade = random.randint(1, 5)
        preco_unitario = round(random.uniform(50.0, 2000.0), 2)
        
        # Data do pedido pode ser alguns dias atrás para variar
        dias_atras = random.randint(0, 7)
        data_pedido = datetime.now() - timedelta(days=dias_atras)
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO public.pedidos (cliente_id, produto, quantidade, preco_unitario, data_pedido)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, (cliente_id, produto, quantidade, preco_unitario, data_pedido))
        
        pedido_id = cur.fetchone()[0]
        valor_total = quantidade * preco_unitario
        print(f"🛒 Pedido inserido: ID {pedido_id} - Cliente {cliente_id} - {produto} (Qtd: {quantidade}, Total: R$ {valor_total:.2f})")
        return pedido_id
        
    except Exception as e:
        print(f"❌ Erro ao inserir pedido: {e}")
        return None

def atualizar_cliente(conn):
    """Atualiza um cliente existente (simula CDC)"""
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nome, email FROM public.clientes ORDER BY RANDOM() LIMIT 1")
        result = cur.fetchone()
        if not result:
            return None
            
        cliente_id, nome_atual, email_atual = result
        
        # Simula atualização de email
        novo_email = gerar_email(nome_atual)
        
        cur.execute("""
            UPDATE public.clientes 
            SET email = %s, ultima_atualizacao = %s
            WHERE id = %s
        """, (novo_email, datetime.now(), cliente_id))
        
        print(f"🔄 Cliente atualizado: ID {cliente_id} - Email: {email_atual} → {novo_email}")
        return cliente_id
        
    except Exception as e:
        print(f"❌ Erro ao atualizar cliente: {e}")
        return None

def mostrar_estatisticas(conn):
    """Mostra estatísticas atuais do banco"""
    try:
        cur = conn.cursor()
        
        # Contagem de clientes
        cur.execute("SELECT COUNT(*) FROM public.clientes")
        total_clientes = cur.fetchone()[0]
        
        # Contagem de pedidos
        cur.execute("SELECT COUNT(*) FROM public.pedidos")
        total_pedidos = cur.fetchone()[0]
        
        # Receita total
        cur.execute("SELECT SUM(quantidade * preco_unitario) FROM public.pedidos")
        receita_total = cur.fetchone()[0] or 0
        
        # Último pedido
        cur.execute("""
            SELECT p.id, c.nome, p.produto, (p.quantidade * p.preco_unitario) as valor_total
            FROM public.pedidos p 
            JOIN public.clientes c ON p.cliente_id = c.id 
            ORDER BY p.id DESC LIMIT 1
        """)
        ultimo_pedido = cur.fetchone()
        
        print(f"\n📊 ESTATÍSTICAS ATUAIS:")
        print(f"   👥 Clientes: {total_clientes}")
        print(f"   🛒 Pedidos: {total_pedidos}")
        print(f"   💰 Receita Total: R$ {receita_total:.2f}")
        if ultimo_pedido:
            print(f"   🔥 Último Pedido: ID {ultimo_pedido[0]} - {ultimo_pedido[1]} - {ultimo_pedido[2]} (R$ {ultimo_pedido[3]:.2f})")
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ Erro ao mostrar estatísticas: {e}")

def main():
    print("🎬 SIMULADOR DE DADOS EM TEMPO REAL")
    print("==================================")
    print("🎯 Objetivo: Demonstrar CDC e Pipeline funcionando")
    print("⏱️  Pressione Ctrl+C para parar\n")
    
    # Conectar ao banco
    conn = conectar_db()
    if not conn:
        sys.exit(1)
    
    try:
        ciclo = 0
        while True:
            ciclo += 1
            print(f"\n🔄 CICLO {ciclo} - {datetime.now().strftime('%H:%M:%S')}")
            
            # Decisão aleatória do que fazer
            acao = random.choices(
                ['novo_cliente', 'novo_pedido', 'atualizar_cliente', 'pedido_cliente_novo'],
                weights=[20, 40, 15, 25],  # Probabilidades
                k=1
            )[0]
            
            if acao == 'novo_cliente':
                inserir_cliente(conn)
                
            elif acao == 'novo_pedido':
                inserir_pedido(conn)
                
            elif acao == 'atualizar_cliente':
                atualizar_cliente(conn)
                
            elif acao == 'pedido_cliente_novo':
                # Cria cliente e pedido na sequência
                cliente_id = inserir_cliente(conn)
                if cliente_id:
                    time.sleep(1)  # Pequena pausa
                    inserir_pedido(conn, cliente_id)
            
            # Mostra estatísticas a cada 10 ciclos
            if ciclo % 10 == 0:
                mostrar_estatisticas(conn)
            
            # Pausa entre inserções (simula tempo real)
            intervalo = random.uniform(2, 8)  # Entre 2 e 8 segundos
            print(f"⏳ Aguardando {intervalo:.1f}s...")
            time.sleep(intervalo)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Simulação interrompida pelo usuário")
        print(f"📈 Total de ciclos executados: {ciclo}")
        mostrar_estatisticas(conn)
        
    except Exception as e:
        print(f"❌ Erro durante simulação: {e}")
        
    finally:
        conn.close()
        print("🔚 Conexão fechada. Obrigado!")

if __name__ == "__main__":
    main() 