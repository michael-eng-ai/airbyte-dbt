-- models/silver/silver_pedidos.sql

-- Este modelo transforma os dados brutos dos pedidos da camada bronze,
-- aplicando limpezas, padronizações e cálculos.

WITH bronze_pedidos AS (
    SELECT
        id AS pedido_id_origem,
        cliente_id AS cliente_id_origem,
        produto,
        quantidade,
        preco_unitario,
        data_pedido,
        ultima_atualizacao,
        _airbyte_emitted_at AS data_replicacao_airbyte
    FROM
        {{ ref('bronze_pedidos') }}
)

SELECT
    p.pedido_id_origem,
    p.cliente_id_origem,
    TRIM(p.produto) AS produto_nome,
    p.quantidade,
    CAST(p.preco_unitario AS DECIMAL(18, 2)) AS preco_unitario_decimal,
    (p.quantidade * CAST(p.preco_unitario AS DECIMAL(18, 2))) AS valor_total_pedido,
    CAST(p.data_pedido AS TIMESTAMP) AS data_pedido_ts,
    CAST(p.ultima_atualizacao AS TIMESTAMP) AS ultima_atualizacao_ts,
    p.data_replicacao_airbyte,
    EXTRACT(YEAR FROM CAST(p.data_pedido AS TIMESTAMP)) AS ano_pedido,
    EXTRACT(MONTH FROM CAST(p.data_pedido AS TIMESTAMP)) AS mes_pedido,
    EXTRACT(DAY FROM CAST(p.data_pedido AS TIMESTAMP)) AS dia_pedido
FROM
    bronze_pedidos p
WHERE
    p.quantidade > 0 AND p.preco_unitario > 0 -- Garante dados válidos

-- Adicionar aqui mais transformações conforme necessário:
-- - Categorização de produtos
-- - Junção com tabela de clientes para obter informações do cliente no mesmo modelo (se fizer sentido)
-- - Tratamento de devoluções ou cancelamentos (se aplicável)