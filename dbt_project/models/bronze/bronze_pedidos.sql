-- models/bronze/bronze_pedidos.sql

-- Seleciona todos os dados da tabela de pedidos da fonte airbyte_raw_data

SELECT
    id,
    cliente_id,
    produto,
    quantidade,
    preco_unitario,
    data_pedido,
    ultima_atualizacao,
    _airbyte_ab_id,
    _airbyte_emitted_at,
    _airbyte_normalized_at,
    _airbyte_pedidos_hashid
FROM
    {{ source('airbyte_raw_data', 'pedidos') }}