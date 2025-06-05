-- models/silver/silver_clientes.sql

-- Este modelo transforma os dados brutos dos clientes da camada bronze,
-- aplicando limpezas, padronizações e enriquecimentos.

{{ config(
    tags=["silver"],
    materialized='table'
) }}

WITH bronze_clientes AS (
    SELECT
        id AS cliente_id_origem,
        nome,
        email,
        telefone,
        cpf,
        data_nascimento,
        endereco,
        status,
        tipo_cliente,
        limite_credito,
        data_cadastro,
        updated_at
    FROM
        {{ ref('bronze_clientes') }}
)

SELECT
    cliente_id_origem,
    INITCAP(TRIM(nome)) AS nome_completo,
    LOWER(TRIM(email)) AS email_padronizado,
    telefone,
    cpf,
    data_nascimento,
    endereco,
    status,
    tipo_cliente,
    limite_credito,
    CAST(data_cadastro AS TIMESTAMP) AS data_cadastro_ts,
    CAST(updated_at AS TIMESTAMP) AS updated_at_ts,
    CURRENT_TIMESTAMP AS data_processamento,
    -- Colunas derivadas
    SUBSTRING(email FROM POSITION('@' IN email) + 1) AS dominio_email,
    EXTRACT(YEAR FROM CAST(data_cadastro AS TIMESTAMP)) AS ano_cadastro,
    CASE 
        WHEN data_nascimento IS NOT NULL 
        THEN EXTRACT(YEAR FROM AGE(data_nascimento))
        ELSE NULL 
    END AS idade_estimada
FROM
    bronze_clientes
WHERE
    email IS NOT NULL 
    AND nome IS NOT NULL

-- Adicionar aqui mais transformações conforme necessário:
-- - Validação de formato de email
-- - Tratamento de dados nulos ou inválidos
-- - Junção com outras tabelas para enriquecimento (ex: dados demográficos)