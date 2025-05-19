-- models/staging/stg_clientes.sql
-- Este modelo representa a tabela de clientes da camada de staging.
-- Ele seleciona as colunas relevantes da fonte de dados bruta (replicada pelo Airbyte)
-- e aplica renomeações e casts básicos, se necessário.

WITH source_clientes AS (
    -- A função source() é usada para referenciar tabelas definidas em seu arquivo sources.yml
    SELECT
        id AS cliente_id, -- Renomeando para clareza e padronização
        nome,
        email,
        data_cadastro,
        ultima_atualizacao,
        _airbyte_emitted_at -- Coluna do Airbyte que indica quando o registro foi emitido
        -- Adicione outras colunas que o Airbyte possa adicionar, como _airbyte_ab_id, _airbyte_clientes_hashid, etc., se precisar delas.
    FROM {{ source('airbyte_raw_data', 'clientes') }}
)

SELECT
    cliente_id,
    nome,
    email,
    CAST(data_cadastro AS TIMESTAMP) AS data_cadastro, -- Exemplo de cast, ajuste conforme o tipo de dado original
    CAST(ultima_atualizacao AS TIMESTAMP) AS ultima_atualizacao,
    CAST(_airbyte_emitted_at AS TIMESTAMP) AS data_ingestao_airbyte
FROM
    source_clientes

-- Condições de filtro podem ser adicionadas aqui se necessário para excluir registros de teste, etc.
-- WHERE ...

-- Adicionando testes de qualidade de dados
-- {{ config(post_hook="ALTER TABLE {{ this }} ADD CONSTRAINT stg_clientes_pk PRIMARY KEY (cliente_id);") }}
