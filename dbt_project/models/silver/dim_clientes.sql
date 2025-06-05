-- models/silver/dim_clientes.sql
-- Este modelo cria a dimensão de clientes, limpando e transformando os dados de bronze_clientes.

{{ config(
    materialized='table',
    tags=['silver', 'dimension']
) }}

-- Silver: Dimensão de clientes limpa e enriquecida
-- Estrutura empresarial completa

SELECT
    id as cliente_id,
    nome,
    LOWER(TRIM(email)) as email_limpo,
    email as email_original,
    telefone,
    cpf,
    data_nascimento,
    endereco,
    status,
    tipo_cliente,
    limite_credito,
    data_cadastro,
    updated_at,
    CASE 
        WHEN data_cadastro >= CURRENT_DATE - INTERVAL '30 days' THEN 'Novo'
        WHEN data_cadastro >= CURRENT_DATE - INTERVAL '365 days' THEN 'Recente'
        ELSE 'Antigo'
    END as categoria_cliente,
    CASE 
        WHEN email LIKE '%@gmail.com' THEN 'Gmail'
        WHEN email LIKE '%@outlook.com' THEN 'Outlook'
        WHEN email LIKE '%@yahoo.com' THEN 'Yahoo'
        WHEN email LIKE '%@example.com' THEN 'Example'
        ELSE 'Outro'
    END as provedor_email,
    CASE 
        WHEN tipo_cliente = 'pessoa_fisica' THEN 'PF'
        WHEN tipo_cliente = 'pessoa_juridica' THEN 'PJ'
        ELSE 'Outro'
    END as tipo_cliente_abrev,
    CASE 
        WHEN limite_credito >= 10000 THEN 'Alto'
        WHEN limite_credito >= 5000 THEN 'Médio'
        WHEN limite_credito > 0 THEN 'Baixo'
        ELSE 'Sem Limite'
    END as categoria_credito
FROM {{ ref('bronze_clientes') }}
WHERE nome IS NOT NULL
