-- Configuração para Change Data Capture (CDC) no PostgreSQL
-- Este script configura o banco para suportar replicação lógica com Airbyte

-- Configurar parâmetros para replicação lógica
-- NOTA: wal_level=logical deve ser configurado no postgresql.conf

-- Criar usuário de replicação (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'airbyte_replication') THEN
        CREATE ROLE airbyte_replication WITH LOGIN PASSWORD 'airbyte_pass' REPLICATION;
    END IF;
END
$$;

-- Dar permissões necessárias para o usuário de replicação
GRANT CONNECT ON DATABASE db_source TO airbyte_replication;
GRANT USAGE ON SCHEMA public TO airbyte_replication;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO airbyte_replication;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO airbyte_replication;

-- Permitir que o usuário principal também faça replicação (para facilitar POC)
ALTER USER admin WITH REPLICATION;
GRANT rds_replication TO admin;

-- Criar publicação para todas as tabelas
DROP PUBLICATION IF EXISTS airbyte_publication;
CREATE PUBLICATION airbyte_publication FOR ALL TABLES;

-- Configurar replica identity para as tabelas (necessário para CDC)
ALTER TABLE public.clientes REPLICA IDENTITY FULL;
ALTER TABLE public.pedidos REPLICA IDENTITY FULL;

-- Mostrar status da configuração
SELECT 
    'wal_level' as parametro, 
    setting as valor 
FROM pg_settings 
WHERE name = 'wal_level'
UNION ALL
SELECT 
    'max_wal_senders' as parametro, 
    setting as valor 
FROM pg_settings 
WHERE name = 'max_wal_senders'
UNION ALL
SELECT 
    'max_replication_slots' as parametro, 
    setting as valor 
FROM pg_settings 
WHERE name = 'max_replication_slots';

-- Listar publicações criadas
SELECT pubname, puballtables FROM pg_publication;

-- Mostrar tabelas com replica identity configurada
SELECT 
    schemaname, 
    tablename, 
    CASE relreplident
        WHEN 'd' THEN 'default'
        WHEN 'f' THEN 'full'
        WHEN 'i' THEN 'index'
        WHEN 'n' THEN 'nothing'
    END as replica_identity
FROM pg_tables t
JOIN pg_class c ON t.tablename = c.relname
WHERE schemaname = 'public';