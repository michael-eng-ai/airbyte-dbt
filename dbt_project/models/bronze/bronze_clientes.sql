-- models/bronze/bronze_clientes.sql

-- Seleciona todos os dados da tabela de clientes da fonte airbyte_raw_data
-- Esta é uma visão simples dos dados brutos, sem transformações complexas ainda.

SELECT
    id,
    nome,
    email,
    data_cadastro,
    ultima_atualizacao,
    _airbyte_ab_id,
    _airbyte_emitted_at,
    _airbyte_normalized_at,
    _airbyte_clientes_hashid
FROM
    {{ source('airbyte_raw_data', 'clientes') }}