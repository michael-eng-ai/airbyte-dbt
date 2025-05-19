import psycopg2
from faker import Faker
import time
import os
import random
import logging
from typing import Optional, Tuple, Dict, Any  # Adicionando type hints adequados

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_populator')

# Configurações do banco de dados
DB_CONFIG: Dict[str, str] = {
    "host": os.getenv("DB_HOST", "postgres_source_db"),
    "dbname": os.getenv("DB_NAME", "db_source"),
    "user": os.getenv("DB_USER", "user_source"),
    "password": os.getenv("DB_PASSWORD", "password_source"),
    "port": os.getenv("DB_PORT", "5432")
}

fake = Faker('pt_BR')

def get_db_connection():
    """Estabelece conexão com o banco de dados PostgreSQL.
    
    Returns:
        psycopg2.connection: Objeto de conexão com o banco de dados
        
    Raises:
        psycopg2.OperationalError: Quando não é possível estabelecer conexão após 5 tentativas
    """
    for i in range(5):  # Tentar conectar algumas vezes
        try:
            conn = psycopg2.connect(
                host=DB_HOST, 
                dbname=DB_NAME, 
                user=DB_USER, 
                password=DB_PASSWORD, 
                port=DB_PORT
            )
            print(f"Conexão com o banco de dados {DB_NAME} em {DB_HOST}:{DB_PORT} bem-sucedida.")
            return conn
        except psycopg2.OperationalError as e:
            print(f"Tentativa {i+1} falhou: Erro de conexão com o banco de dados: {e}")
            if i < 4:
                time.sleep(5)  # Esperar 5 segundos antes de tentar novamente
            else:
                raise
    raise psycopg2.OperationalError(f"Não foi possível conectar ao {DB_HOST}:{DB_PORT} após 5 tentativas")

def insert_cliente(conn) -> Optional[int]:
    """Insere um novo cliente fictício.
    
    Args:
        conn: Conexão com o banco de dados
        
    Returns:
        int: ID do cliente inserido, ou None se ocorrer um erro
    """
    cur = conn.cursor()
    nome = fake.name()
    email = fake.unique.email()  # Garante email único por execução do Faker
    try:
        cur.execute(
            "INSERT INTO public.clientes (nome, email, data_cadastro, ultima_atualizacao) VALUES (%s, %s, NOW(), NOW()) RETURNING id, nome;",
            (nome, email)
        )
        cliente_id, nome_cliente = cur.fetchone()
        conn.commit()
        print(f"Cliente inserido: ID={cliente_id}, Nome='{nome_cliente}'")
        return cliente_id
    except psycopg2.IntegrityError:
        conn.rollback()
        print(f"Erro ao inserir cliente (email duplicado?): {email}")
        return None
    finally:
        cur.close()

def insert_pedido(conn, cliente_id: int) -> Optional[int]:
    """Insere um novo pedido fictício para um cliente.
    
    Args:
        conn: Conexão com o banco de dados
        cliente_id: ID do cliente ao qual o pedido pertence
        
    Returns:
        int: ID do pedido inserido, ou None se ocorrer um erro
    """
    cur = conn.cursor()
    produto = fake.random_element(elements=('Produto X', 'Produto Y', 'Produto Z', 'Serviço A', 'Serviço B'))
    quantidade = fake.random_int(min=1, max=10)
    preco_unitario = round(random.uniform(10.0, 200.0), 2)

    try:
        cur.execute(
            "INSERT INTO public.pedidos (cliente_id, produto, quantidade, preco_unitario, data_pedido, ultima_atualizacao) VALUES (%s, %s, %s, %s, NOW(), NOW()) RETURNING id, produto;",
            (cliente_id, produto, quantidade, preco_unitario)
        )
        pedido_id, nome_produto = cur.fetchone()
        conn.commit()
        print(f"Pedido inserido: ID={pedido_id}, Produto='{nome_produto}' para Cliente ID={cliente_id}")
        return pedido_id
    except Exception as e:
        conn.rollback()
        print(f"Erro ao inserir pedido para cliente {cliente_id}: {e}")
        return None
    finally:
        cur.close()

def update_random_cliente(conn) -> bool:
    """Atualiza o email de um cliente aleatório existente.
    
    Args:
        conn: Conexão com o banco de dados
        
    Returns:
        bool: True se a atualização for bem-sucedida, False caso contrário
    """
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM public.clientes ORDER BY RANDOM() LIMIT 1;")
        result = cur.fetchone()
        if not result:
            print("Nenhum cliente encontrado para atualização.")
            return False

        cliente_id_para_atualizar = result[0]
        novo_email = fake.unique.email()  # Garante email único

        cur.execute(
            "UPDATE public.clientes SET email = %s, ultima_atualizacao = NOW() WHERE id = %s RETURNING nome;",
            (novo_email, cliente_id_para_atualizar)
        )
        if cur.rowcount > 0:
            nome_cliente = cur.fetchone()[0]
            conn.commit()
            print(f"Cliente atualizado: ID={cliente_id_para_atualizar}, Nome='{nome_cliente}', Novo Email='{novo_email}'")
            return True
        else:
            print(f"Cliente com ID={cliente_id_para_atualizar} não encontrado no momento da atualização.")
            return False
    except psycopg2.IntegrityError:
        conn.rollback()
        print(f"Erro de integridade ao atualizar cliente {cliente_id_para_atualizar} (email duplicado?): {novo_email}")
        return False
    except Exception as e:
        conn.rollback()
        print(f"Erro ao atualizar cliente {cliente_id_para_atualizar}: {e}")
        return False
    finally:
        cur.close()

def delete_random_cliente(conn) -> bool:
    """Exclui um cliente aleatório para testar CDC em operações DELETE.
    
    Args:
        conn: Conexão com o banco de dados
        
    Returns:
        bool: True se a exclusão for bem-sucedida, False caso contrário
    """
    cur = conn.cursor()
    try:
        # Seleciona um cliente com poucos ou nenhum pedido para minimizar problemas de chave estrangeira
        cur.execute("""
            SELECT c.id 
            FROM public.clientes c 
            LEFT JOIN public.pedidos p ON c.id = p.cliente_id 
            GROUP BY c.id 
            HAVING COUNT(p.id) <= 1 
            ORDER BY RANDOM() 
            LIMIT 1;
        """)
        result = cur.fetchone()
        if not result:
            print("Nenhum cliente adequado para exclusão.")
            return False

        cliente_id = result[0]
        
        # Primeiro exclui os pedidos relacionados
        cur.execute("DELETE FROM public.pedidos WHERE cliente_id = %s RETURNING id;", (cliente_id,))
        pedidos_excluidos = cur.rowcount
        
        # Agora exclui o cliente
        cur.execute("DELETE FROM public.clientes WHERE id = %s RETURNING nome;", (cliente_id,))
        if cur.rowcount > 0:
            nome_cliente = cur.fetchone()[0]
            conn.commit()
            print(f"Cliente excluído: ID={cliente_id}, Nome='{nome_cliente}' (e {pedidos_excluidos} pedidos relacionados)")
            return True
        else:
            print(f"Cliente com ID={cliente_id} não encontrado no momento da exclusão.")
            conn.rollback()
            return False
    except Exception as e:
        conn.rollback()
        print(f"Erro ao excluir cliente: {e}")
        return False
    finally:
        cur.close()

if __name__ == "__main__":
    try:
        # Usando gerenciador de contexto (with) para garantir fechamento da conexão
        with get_db_connection() as conn:
            # Inserir novos clientes e pedidos
            num_novos_clientes = 2
            print(f"\n--- Inserindo {num_novos_clientes} novos clientes e seus pedidos ---")
            for i in range(num_novos_clientes):
                cliente_id = insert_cliente(conn)
                if cliente_id:
                    for _ in range(fake.random_int(min=0, max=2)):  # Inserir 0 a 2 pedidos por novo cliente
                        insert_pedido(conn, cliente_id)
                time.sleep(0.5)  # Pequena pausa

            # Atualizar um cliente existente (para testar CDC em updates)
            print("\n--- Tentativa de atualização de um cliente aleatório ---")
            update_random_cliente(conn)
            
            # Nova operação: Excluir um cliente (para testar CDC em deletes)
            print("\n--- Tentativa de exclusão de um cliente aleatório ---")
            delete_random_cliente(conn)

            print("\nPopulação/atualização/exclusão de dados fictícios concluída.")

    except psycopg2.OperationalError as e:
        print(f"Não foi possível conectar ao banco de dados após várias tentativas.")
        print(f"Verifique se o serviço 'postgres_source_db' está rodando e acessível em {DB_HOST}:{DB_PORT}.")
    except Exception as e:
        print(f"Um erro geral ocorreu: {e}")