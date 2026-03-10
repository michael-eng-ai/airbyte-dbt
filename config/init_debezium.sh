#!/usr/bin/env bash
# Registra o conector Debezium no Kafka Connect após o serviço estar pronto.
# Pode ser executado manualmente ou pelo docker-compose init hook.

set -e

CONNECT_URL="http://localhost:8083"
CONNECTOR_FILE="$(dirname "$0")/debezium-connector.json"

echo "Aguardando Kafka Connect ficar disponível..."
until curl -sf "${CONNECT_URL}/connectors" > /dev/null 2>&1; do
  echo "  Kafka Connect ainda não está pronto. Aguardando 5s..."
  sleep 5
done

echo "Kafka Connect disponível!"

# Se o conector já existe, apaga para recriar (idempotente)
if curl -sf "${CONNECT_URL}/connectors/postgres-source-connector" > /dev/null 2>&1; then
  echo "Conector já existe. Removendo para recriar..."
  curl -sf -X DELETE "${CONNECT_URL}/connectors/postgres-source-connector"
  sleep 2
fi

# Cria a publication e o slot no postgres_source (idempotente)
echo "Criando publication e replication slot no PostgreSQL Source..."
docker exec postgres_source_db psql -U admin -d db_source << 'PSQL'
-- Slot Debezium
SELECT pg_create_logical_replication_slot('debezium_slot', 'pgoutput')
WHERE NOT EXISTS (
  SELECT 1 FROM pg_replication_slots WHERE slot_name = 'debezium_slot'
);

-- Publica todas as tabelas relevantes
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'debezium_publication') THEN
    EXECUTE 'CREATE PUBLICATION debezium_publication FOR TABLE clientes, pedidos, produtos, leads';
  END IF;
END $$;
PSQL

echo "Registrando conector Debezium..."
curl -sf -X POST "${CONNECT_URL}/connectors" \
  -H "Content-Type: application/json" \
  --data @"${CONNECTOR_FILE}"

echo ""
echo "Aguardando conector atingir estado RUNNING..."
for i in $(seq 1 30); do
  STATUS=$(curl -sf "${CONNECT_URL}/connectors/postgres-source-connector/status" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('connector',{}).get('state','?'))" 2>/dev/null)
  echo "  Estado do conector: ${STATUS} (tentativa ${i}/30)"
  if [ "${STATUS}" = "RUNNING" ]; then
    echo "Conector RUNNING! Topics disponíveis em kafka:29092"
    echo ""
    echo "Topics esperados:"
    echo "  dbserver1.public.clientes"
    echo "  dbserver1.public.pedidos"
    echo "  dbserver1.public.produtos"
    echo "  dbserver1.public.leads"
    exit 0
  fi
  sleep 3
done

echo "ERRO: Conector não atingiu estado RUNNING em 90s. Verifique os logs:"
echo "  docker logs kafka_connect"
exit 1
