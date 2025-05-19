#!/bin/bash

# Script para configurar automaticamente a conexão HTTP do Airflow para o Airbyte
# Será executado após a inicialização do Airflow

# Espera o Airflow webserver estar disponível
echo "Aguardando o Airflow webserver estar disponível..."
while ! curl --output /dev/null --silent --head --fail http://airflow-webserver:8080/health; do
  sleep 5
done

echo "Configurando conexão do Airflow com o Airbyte..."

# Cria a conexão HTTP para o Airbyte - ajuste as credenciais se necessário
airflow connections add 'airbyte_conn' \
  --conn-type 'http' \
  --conn-host "${AIRBYTE_HOST:-airbyte-server}" \
  --conn-port "${AIRBYTE_PORT:-8000}" \
  --conn-schema 'http' \
  --conn-extra '{"endpoint": "/api/v1"}'

echo "Conexão airbyte_conn configurada com sucesso!"

# Mantém o container rodando para executar outros comandos se necessário
tail -f /dev/null