-- models/bronze/stg_pedidos.sql
-- Este modelo representa a tabela de pedidos da camada de staging (bronze).

WITH source_pedidos AS (
    SELECT
        id AS pedido_id,
        cliente_id,
        produto,
        quantidade,
        preco_unitario,
        data_pedido,
        ultima_atualizacao,
        _airbyte_emitted_at
    FROM {{ source('airbyte_raw_data', 'pedidos') }}
)

SELECT
    pedido_id,
    cliente_id,
    produto,
    quantidade,
    preco_unitario,
    CAST(data_pedido AS TIMESTAMP) AS data_pedido,
    CAST(ultima_atualizacao AS TIMESTAMP) AS ultima_atualizacao,
    CAST(_airbyte_emitted_at AS TIMESTAMP) AS data_ingestao_airbyte
FROM
    source_pedidos

-- Adicionando testes de qualidade de dados
-- {{ config(post_hook="ALTER TABLE {{ this }} ADD CONSTRAINT stg_pedidos_pk PRIMARY KEY (pedido_id);") }}
