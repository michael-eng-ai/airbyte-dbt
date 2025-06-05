-- models/silver/silver_pedidos.sql

-- Este modelo transforma os dados brutos dos pedidos da camada bronze,
-- aplicando limpezas, padronizações e cálculos.

{{ config(
    tags=["silver"],
    materialized='table'
) }}

WITH bronze_pedidos AS (
    SELECT
        id AS pedido_id_origem,
        cliente_id AS cliente_id_origem,
        numero_pedido,
        data_pedido,
        status,
        valor_bruto,
        desconto,
        valor_liquido,
        metodo_pagamento,
        canal_venda,
        observacoes,
        data_entrega_prevista,
        data_entrega_real,
        updated_at
    FROM
        {{ ref('bronze_pedidos') }}
)

SELECT
    p.pedido_id_origem,
    p.cliente_id_origem,
    TRIM(p.numero_pedido) AS numero_pedido_clean,
    p.status,
    CAST(p.valor_bruto AS DECIMAL(18, 2)) AS valor_bruto_decimal,
    CAST(p.desconto AS DECIMAL(18, 2)) AS desconto_decimal,
    CAST(p.valor_liquido AS DECIMAL(18, 2)) AS valor_liquido_decimal,
    p.metodo_pagamento,
    p.canal_venda,
    p.observacoes,
    CAST(p.data_pedido AS TIMESTAMP) AS data_pedido_ts,
    p.data_entrega_prevista,
    p.data_entrega_real,
    CAST(p.updated_at AS TIMESTAMP) AS updated_at_ts,
    CURRENT_TIMESTAMP AS data_processamento,
    EXTRACT(YEAR FROM CAST(p.data_pedido AS TIMESTAMP)) AS ano_pedido,
    EXTRACT(MONTH FROM CAST(p.data_pedido AS TIMESTAMP)) AS mes_pedido,
    EXTRACT(DAY FROM CAST(p.data_pedido AS TIMESTAMP)) AS dia_pedido,
    -- Cálculos derivados
    CASE 
        WHEN p.valor_bruto > 0 
        THEN (p.desconto / p.valor_bruto * 100)
        ELSE 0 
    END AS percentual_desconto,
    CASE 
        WHEN p.data_entrega_real IS NOT NULL AND p.data_entrega_prevista IS NOT NULL
        THEN p.data_entrega_real - p.data_entrega_prevista
        ELSE NULL
    END AS atraso_entrega_dias
FROM
    bronze_pedidos p
WHERE
    p.valor_bruto > 0 -- Garante dados válidos

-- Adicionar aqui mais transformações conforme necessário:
-- - Categorização de produtos
-- - Junção com tabela de clientes para obter informações do cliente no mesmo modelo (se fizer sentido)
-- - Tratamento de devoluções ou cancelamentos (se aplicável)