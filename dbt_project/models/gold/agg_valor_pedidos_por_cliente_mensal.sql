-- models/gold/agg_valor_pedidos_por_cliente_mensal.sql
-- Este modelo agrega o valor total de pedidos por cliente e por mês.
-- É um exemplo de modelo da camada Gold, pronto para consumo por ferramentas de BI ou dashboards.

WITH fct_pedidos AS (
    SELECT
        cliente_id,
        nome_cliente,
        ano_pedido,
        mes_pedido,
        valor_liquido,
        pedido_id
    FROM {{ ref('fct_pedidos') }}
)

SELECT
    cliente_id,
    nome_cliente,
    ano_pedido,
    mes_pedido,
    SUM(valor_liquido) AS valor_total_pedidos_mensal,
    COUNT(DISTINCT pedido_id) AS numero_de_pedidos_mensal
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
