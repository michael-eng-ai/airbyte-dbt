-- Script para criar schema, tabelas e popular o banco de dados de origem (postgres_source)

-- Criação de um schema exemplo
CREATE SCHEMA IF NOT EXISTS public;

-- Tabela de Exemplo: Clientes
CREATE TABLE IF NOT EXISTS public.clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    data_cadastro TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ultima_atualizacao TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Exemplo: Pedidos
CREATE TABLE IF NOT EXISTS public.pedidos (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES public.clientes(id),
    produto VARCHAR(255) NOT NULL,
    quantidade INTEGER NOT NULL,
    preco_unitario DECIMAL(10, 2) NOT NULL,
    data_pedido TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ultima_atualizacao TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Inserir dados de exemplo na tabela Clientes
INSERT INTO public.clientes (nome, email) VALUES
('João Silva', 'joao.silva@example.com'),
('Maria Oliveira', 'maria.oliveira@example.com'),
('Carlos Pereira', 'carlos.pereira@example.com')
ON CONFLICT (email) DO NOTHING;

-- Inserir dados de exemplo na tabela Pedidos
INSERT INTO public.pedidos (cliente_id, produto, quantidade, preco_unitario) VALUES
(1, 'Produto A', 2, 50.00),
(1, 'Produto B', 1, 120.50),
(2, 'Produto C', 3, 25.75),
(3, 'Produto A', 1, 50.00),
(2, 'Produto B', 5, 120.50)
ON CONFLICT DO NOTHING;

-- Função para atualizar o campo ultima_atualizacao automaticamente
CREATE OR REPLACE FUNCTION update_ultima_atualizacao_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.ultima_atualizacao = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para a tabela Clientes
DO $$
BEGIN
   IF NOT EXISTS (
       SELECT 1
       FROM pg_trigger
       WHERE tgname = 'update_clientes_modtime'
   ) THEN
       CREATE TRIGGER update_clientes_modtime
       BEFORE UPDATE ON public.clientes
       FOR EACH ROW
       EXECUTE FUNCTION update_ultima_atualizacao_column();
   END IF;
END
$$;

-- Triggers para a tabela Pedidos
DO $$
BEGIN
   IF NOT EXISTS (
       SELECT 1
       FROM pg_trigger
       WHERE tgname = 'update_pedidos_modtime'
   ) THEN
       CREATE TRIGGER update_pedidos_modtime
       BEFORE UPDATE ON public.pedidos
       FOR EACH ROW
       EXECUTE FUNCTION update_ultima_atualizacao_column();
   END IF;
END
$$;

-- Para que o CDC funcione corretamente com Airbyte, o usuário do banco de dados
-- que o Airbyte usará para se conectar ao `postgres_source` precisa ter permissões de replicação.
-- E o `wal_level` precisa ser `logical` no `postgresql.conf`.
-- No `docker-compose.yml`, o `postgres_source` já está configurado com usuário e senha.
-- O comando abaixo seria executado DENTRO do container postgres_source ou por um superusuário.
-- ALTER USER user_source WITH REPLICATION;

-- Adicionalmente, para o Airbyte criar a publicação e o slot de replicação,
-- o usuário `user_source` precisará de permissões para criar publicações e slots de replicação.
-- GRANT CREATE ON DATABASE db_source TO user_source;

-- NOTA: A configuração completa do CDC (wal_level, permissões de replicação) é mais complexa
-- e pode exigir ajustes no arquivo de configuração do PostgreSQL (postgresql.conf) dentro do container
-- ou uma imagem Docker do Postgres já preparada para replicação lógica (ex: debezium/postgres).
-- Para este exemplo, focaremos na estrutura e no fluxo de dados inicial.
-- O Airbyte usará o modo de captura de dados padrão (leitura de tabelas) se o CDC não estiver totalmente configurado.
