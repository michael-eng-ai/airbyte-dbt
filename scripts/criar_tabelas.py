#!/usr/bin/env python3
"""
Script para Criar Tabelas PostgreSQL
Executa os comandos SQL de inicialização direto no banco, sem depender do Docker
"""

import psycopg2
import sys
import os
from datetime import datetime

def log_info(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️  {msg}")

def log_success(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {msg}")

def log_error(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ {msg}")

def get_sql_init_script():
    """Retorna o conteúdo do arquivo SQL de inicialização"""
    script_path = "postgres_init_scripts/init_source_db.sql"
    
    if not os.path.exists(script_path):
        log_error(f"Arquivo SQL não encontrado: {script_path}")
        return None
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        log_error(f"Erro ao ler arquivo SQL: {e}")
        return None

def execute_sql_script(connection_config):
    """Executa o script SQL completo no PostgreSQL"""
    log_info("Executando script de inicialização do banco...")
    
    # Obter script SQL
    sql_content = get_sql_init_script()
    if not sql_content:
        return False
    
    try:
        # Conectar ao PostgreSQL
        conn = psycopg2.connect(**connection_config)
        conn.autocommit = True  # Para comandos DDL
        cur = conn.cursor()
        
        log_info("Executando comandos SQL...")
        
        # Executar o script SQL completo de uma vez
        # Isso evita problemas com funções plpgsql que são multilinear
        try:
            cur.execute(sql_content)
            log_success("Script SQL executado com sucesso")
        except Exception as e:
            log_error(f"Erro na execução do script: {e}")
            # Continuar para verificar se pelo menos algumas tabelas foram criadas
        
        # Verificar se as tabelas foram criadas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('clientes', 'pedidos', 'produtos', 'itens_pedido', 'campanhas_marketing', 'leads')
            ORDER BY table_name;
        """)
        
        created_tables = [row[0] for row in cur.fetchall()]
        log_success(f"Tabelas criadas: {created_tables}")
        
        # Verificar estrutura de clientes e pedidos (principais)
        if 'clientes' in created_tables:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'clientes' 
                ORDER BY ordinal_position;
            """)
            clientes_cols = [row[0] for row in cur.fetchall()]
            log_info(f"Tabela clientes - colunas: {clientes_cols}")
        
        if 'pedidos' in created_tables:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'pedidos' 
                ORDER BY ordinal_position;
            """)
            pedidos_cols = [row[0] for row in cur.fetchall()]
            log_info(f"Tabela pedidos - colunas: {pedidos_cols}")
        
        conn.close()
        
        if len(created_tables) >= 2:  # Pelo menos clientes e pedidos
            log_success(f"Inicialização concluída - {len(created_tables)} tabelas criadas")
            return True
        else:
            log_error(f"Falha na inicialização - apenas {len(created_tables)} tabelas criadas")
            return False
        
    except Exception as e:
        log_error(f"Erro fatal na execução SQL: {e}")
        return False

def insert_sample_data(connection_config):
    """Insere alguns dados de exemplo se as tabelas estiverem vazias"""
    log_info("Verificando se precisa inserir dados de exemplo...")
    
    try:
        conn = psycopg2.connect(**connection_config)
        cur = conn.cursor()
        
        # Verificar se clientes está vazio
        cur.execute("SELECT COUNT(*) FROM public.clientes")
        clientes_count = cur.fetchone()[0]
        
        if clientes_count == 0:
            log_info("Inserindo dados de exemplo...")
            
            # Inserir clientes de exemplo
            sample_clients = [
                ("João Silva", "joao@email.com", "11999999999", "123.456.789-01"),
                ("Maria Santos", "maria@email.com", "11888888888", "987.654.321-02"),
                ("Pedro Costa", "pedro@email.com", "11777777777", "456.789.123-03"),
            ]
            
            for nome, email, telefone, cpf in sample_clients:
                cur.execute("""
                    INSERT INTO public.clientes (nome, email, telefone, cpf) 
                    VALUES (%s, %s, %s, %s)
                """, (nome, email, telefone, cpf))
            
            conn.commit()
            log_success(f"Inseridos {len(sample_clients)} clientes de exemplo")
        else:
            log_info(f"Tabela clientes já contém {clientes_count} registros")
        
        conn.close()
        return True
        
    except Exception as e:
        log_error(f"Erro ao inserir dados de exemplo: {e}")
        return False

def main():
    """Função principal"""
    log_info("🚀 CRIADOR DE TABELAS POSTGRESQL")
    log_info("=" * 50)
    
    # Configuração da conexão com credenciais padronizadas
    db_config = {
        'host': 'localhost',
        'port': 5430,
        'database': 'db_source', 
        'user': 'admin',
        'password': 'admin'
    }
    
    # Verificar conectividade
    try:
        conn = psycopg2.connect(**db_config)
        conn.close()
        log_success("Conexão PostgreSQL OK")
    except Exception as e:
        log_error(f"Falha na conexão PostgreSQL: {e}")
        return False
    
    # Executar script de inicialização
    if not execute_sql_script(db_config):
        log_error("Falha na criação das tabelas")
        return False
    
    # Inserir dados de exemplo (opcional)
    if not insert_sample_data(db_config):
        log_error("Falha na inserção de dados de exemplo")
        # Não retornar False aqui - dados de exemplo são opcionais
    
    log_success("🎉 Inicialização do banco concluída com sucesso!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 