-- models/gold/agg_valor_pedidos_por_cliente_mensal.sql
-- Este modelo agrega o valor total de pedidos por cliente e por mês.
-- É um exemplo de modelo da camada Gold, pronto para consumo por ferramentas de BI ou dashboards.

WITH fct_pedidos AS (
    SELECT
        cliente_id,
        nome_cliente,
        EXTRACT(YEAR FROM data_pedido) AS ano_pedido,
        EXTRACT(MONTH FROM data_pedido) AS mes_pedido,
        valor_total_pedido
    FROM {{ ref('fct_pedidos') }}
)

SELECT
    cliente_id,
    nome_cliente,
    ano_pedido,
    mes_pedido,
    SUM(valor_total_pedido) AS valor_total_pedidos_mensal,
    COUNT(DISTINCT CASE WHEN valor_total_pedido > 0 THEN cliente_id || '-' || ano_pedido || '-' || mes_pedido END) AS numero_de_pedidos_mensal -- Contagem de pedidos no mês
FROM
    fct_pedidos
GROUP BY
    cliente_id,
    nome_cliente,
    ano_pedido,
    mes_pedido
ORDER BY
    ano_pedido DESC,
    mes_pedido DESC,
    valor_total_pedidos_mensal DESC
