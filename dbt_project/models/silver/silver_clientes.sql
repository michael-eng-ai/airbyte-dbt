-- models/silver/silver_clientes.sql

-- Este modelo transforma os dados brutos dos clientes da camada bronze,
-- aplicando limpezas, padronizações e enriquecimentos.

WITH bronze_clientes AS (
    SELECT
        id AS cliente_id_origem, -- Renomeia para clareza e evitar conflito
        nome,
        email,
        data_cadastro,
        ultima_atualizacao,
        _airbyte_emitted_at AS data_replicacao_airbyte
    FROM
        {{ ref('bronze_clientes') }}
)

SELECT
    cliente_id_origem,
    INITCAP(TRIM(nome)) AS nome_completo, -- Padroniza nome para Title Case e remove espaços extras
    LOWER(TRIM(email)) AS email_padronizado, -- Padroniza email para lowercase e remove espaços extras
    CAST(data_cadastro AS TIMESTAMP) AS data_cadastro_ts,
    CAST(ultima_atualizacao AS TIMESTAMP) AS ultima_atualizacao_ts,
    data_replicacao_airbyte,
    -- Exemplo de coluna derivada: Domínio do email
    SUBSTRING(email FROM POSITION('@' IN email) + 1) AS dominio_email,
    -- Exemplo de coluna derivada: Ano de cadastro
    EXTRACT(YEAR FROM CAST(data_cadastro AS TIMESTAMP)) AS ano_cadastro
FROM
    bronze_clientes
WHERE
    email IS NOT NULL -- Exemplo de filtro para garantir qualidade dos dados
    AND nome IS NOT NULL

-- Adicionar aqui mais transformações conforme necessário:
-- - Validação de formato de email
-- - Tratamento de dados nulos ou inválidos
-- - Junção com outras tabelas para enriquecimento (ex: dados demográficos)