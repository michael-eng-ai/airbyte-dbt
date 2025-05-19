-- models/gold/gold_visao_geral_clientes.sql

-- Este modelo de agregação fornece uma visão geral dos clientes,
-- combinando informações da camada silver de clientes e pedidos.

WITH silver_clientes AS (
    SELECT
        cliente_id_origem,
        nome_completo,
        email_padronizado,
        data_cadastro_ts,
        ultima_atualizacao_ts,
        dominio_email,
        ano_cadastro
    FROM
        {{ ref('silver_clientes') }}
),

silver_pedidos AS (
    SELECT
        cliente_id_origem,
        pedido_id_origem,
        valor_total_pedido,
        data_pedido_ts
    FROM
        {{ ref('silver_pedidos') }}
),

pedidos_agregados_por_cliente AS (
    SELECT
        cliente_id_origem,
        COUNT(pedido_id_origem) AS total_pedidos,
        SUM(valor_total_pedido) AS valor_total_gasto,
        MIN(data_pedido_ts) AS data_primeiro_pedido,
        MAX(data_pedido_ts) AS data_ultimo_pedido
    FROM
        silver_pedidos
    GROUP BY
        cliente_id_origem
)

SELECT
    sc.cliente_id_origem,
    sc.nome_completo,
    sc.email_padronizado,
    sc.data_cadastro_ts,
    sc.ultima_atualizacao_ts AS ultima_atualizacao_cliente_ts,
    sc.dominio_email,
    sc.ano_cadastro,
    COALESCE(pa.total_pedidos, 0) AS total_pedidos_realizados,
    COALESCE(pa.valor_total_gasto, 0.00) AS valor_total_gasto_cliente,
    pa.data_primeiro_pedido,
    pa.data_ultimo_pedido,
    (CASE
        WHEN pa.total_pedidos > 10 THEN 'Cliente VIP'
        WHEN pa.total_pedidos > 5 THEN 'Cliente Regular'
        WHEN pa.total_pedidos > 0 THEN 'Cliente Novo'
        ELSE 'Cliente Inativo (sem pedidos)'
    END) AS segmento_cliente
FROM
    silver_clientes sc
LEFT JOIN
    pedidos_agregados_por_cliente pa ON sc.cliente_id_origem = pa.cliente_id_origem

-- Adicionar aqui mais lógicas de negócio para a camada Gold:
-- - Cálculo de LTV (Lifetime Value)
-- - Análise de Churn
-- - Segmentação avançada de clientes
-- - Métricas de Recência, Frequência, Valor (RFV)