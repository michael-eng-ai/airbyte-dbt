-- models/silver/dim_clientes.sql
-- Este modelo cria a dimensão de clientes, limpando e transformando os dados de stg_clientes.

WITH stg_clientes AS (
    SELECT
        cliente_id,
        nome,
        email,
        data_cadastro,
        ultima_atualizacao,
        data_ingestao_airbyte
    FROM {{ ref('stg_clientes') }}
)

SELECT
    cliente_id,
    TRIM(nome) AS nome, -- Exemplo de limpeza: remover espaços em branco extras
    LOWER(TRIM(email)) AS email, -- Padronizar email para minúsculas e remover espaços
    data_cadastro,
    ultima_atualizacao,
    data_ingestao_airbyte
    -- Adicionar aqui outras transformações ou derivações de colunas, por exemplo:
    -- EXTRACT(YEAR FROM data_cadastro) AS ano_cadastro,
    -- CASE
    --     WHEN email LIKE '%@gmail.com' THEN 'Gmail'
    --     WHEN email LIKE '%@hotmail.com' THEN 'Hotmail'
    --     ELSE 'Outro'
    -- END AS provedor_email
FROM
    stg_clientes
-- WHERE email IS NOT NULL -- Exemplo de filtro para garantir qualidade dos dados
