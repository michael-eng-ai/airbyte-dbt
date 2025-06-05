-- models/bronze/bronze_pedidos.sql

-- Seleciona todos os dados da tabela de pedidos da fonte
-- Esta é uma visão simples dos dados brutos, sem transformações complexas ainda.

{{ config(
    materialized='view',
    tags=['bronze', 'pedidos', 'cdc']
) }}

-- Camada Bronze: Dados brutos de pedidos com schema atualizado

-- Bronze: Dados brutos de pedidos diretamente do source (replicado via Airbyte CDC)
-- Nova estrutura empresarial com campos completos
SELECT 
    id,
    cliente_id,
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
    updated_at,
    created_by,
    version,
    -- Metadados para auditoria CDC
    updated_at as ultima_modificacao_fonte
FROM {{ source('raw_data', 'pedidos') }}
WHERE valor_bruto > 0  -- Validação básica: pedidos devem ter valor positivo