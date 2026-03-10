#!/usr/bin/env python3
"""
Kafka Consumer - Debezium CDC Events → PostgreSQL Target
Lê eventos CDC dos topics Debezium e aplica UPSERT no banco de destino.
Roda como um serviço contínuo.
"""

import os
import json
import logging
import time
import psycopg2
import psycopg2.extras
from datetime import datetime

try:
    from confluent_kafka import Consumer, KafkaError, KafkaException
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "confluent-kafka", "-q"])
    from confluent_kafka import Consumer, KafkaError, KafkaException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger("kafka_consumer")

# ─── Configuração ─────────────────────────────────────────────────────────────

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TARGET_HOST     = os.getenv("TARGET_HOST", "localhost")
TARGET_PORT     = int(os.getenv("TARGET_PORT", "5431"))
TARGET_DB       = os.getenv("TARGET_DB", "db_target")
TARGET_USER     = os.getenv("TARGET_USER", "admin")
TARGET_PASSWORD = os.getenv("TARGET_PASSWORD", "admin")

TOPICS = [
    "dbserver1.public.clientes",
    "dbserver1.public.pedidos",
    "dbserver1.public.produtos",
    "dbserver1.public.leads",
]

# Mapeamento topic → tabela destino e colunas para UPSERT
TABLE_MAP = {
    "dbserver1.public.clientes": {
        "table": "public.clientes",
        "pk": "id",
        "columns": [
            "id", "nome", "email", "telefone", "cpf", "data_nascimento",
            "status", "tipo_cliente", "limite_credito", "data_cadastro",
            "updated_at", "created_by", "version", "endereco",
        ],
    },
    "dbserver1.public.pedidos": {
        "table": "public.pedidos",
        "pk": "id",
        "columns": [
            "id", "cliente_id", "numero_pedido", "data_pedido", "status",
            "valor_bruto", "desconto", "metodo_pagamento",
            "canal_venda", "observacoes", "data_entrega_prevista",
            "data_entrega_real", "updated_at", "created_by", "version",
        ],
    },
    "dbserver1.public.produtos": {
        "table": "public.produtos",
        "pk": "id",
        "columns": [
            "id", "codigo_produto", "nome", "categoria", "preco_custo",
            "preco_venda", "estoque_atual", "ativo", "updated_at",
        ],
    },
    "dbserver1.public.leads": {
        "table": "public.leads",
        "pk": "id",
        "columns": [
            "id", "nome", "email", "telefone", "fonte", "score",
            "status", "interesse", "orcamento_estimado", "data_contato",
            "data_conversao", "updated_at",
        ],
    },
}


# ─── Utilitários ──────────────────────────────────────────────────────────────

def get_db_conn():
    """Cria conexão com o banco target."""
    return psycopg2.connect(
        host=TARGET_HOST, port=TARGET_PORT, dbname=TARGET_DB,
        user=TARGET_USER, password=TARGET_PASSWORD
    )


from datetime import date, timedelta as tdelta, datetime as dt

# Debezium date handling
EPOCH = date(1970, 1, 1)

# Columns that Debezium sends as epoch days (DATE fields)
DATE_COLS = {"data_nascimento", "data_cadastro_date", "data_contato", "data_conversao",
             "data_entrega_prevista", "data_entrega_real"}

# Columns that Debezium sends as epoch milliseconds (TIMESTAMP fields)
TS_COLS = {"data_cadastro", "data_pedido", "updated_at", "data_nascimento_ts"}

# Columns that hold JSON strings (stored as TEXT in target)
JSON_COLS = {"endereco"}


def coerce_payload(payload: dict) -> dict:
    """Convert Debezium wire types to Python / PostgreSQL compatible types."""
    result = {}
    for k, v in payload.items():
        if v is None:
            result[k] = None
        elif k in DATE_COLS and isinstance(v, (int, float)):
            # Debezium DATE = days since epoch
            result[k] = (EPOCH + tdelta(days=int(v))).isoformat()
        elif k in TS_COLS and isinstance(v, (int, float)):
            # Debezium TIMESTAMP = microseconds since epoch
            result[k] = dt.utcfromtimestamp(v / 1_000_000).isoformat()
        elif k in JSON_COLS and isinstance(v, dict):
            result[k] = json.dumps(v, ensure_ascii=False)
        else:
            result[k] = v
    return result


def upsert_row(cur, topic: str, payload: dict) -> str | None:
    """UPSERT de um registro no banco target. Retorna a operação aplicada."""
    cfg     = TABLE_MAP.get(topic)
    if not cfg:
        return None

    table   = cfg["table"]
    pk      = cfg["pk"]
    columns = [c for c in cfg["columns"] if c in payload]

    if not columns or pk not in payload:
        return None

    op = payload.get("__op", "r")  # r=read/snapshot, c=create, u=update, d=delete

    if op == "d":
        cur.execute(f"DELETE FROM {table} WHERE {pk} = %s", (payload[pk],))
        return "DELETE"

    values       = [payload.get(c) for c in columns]
    cols_str     = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    update_cols  = [c for c in columns if c != pk]
    update_str   = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])

    sql = f"""
        INSERT INTO {table} ({cols_str})
        VALUES ({placeholders})
        ON CONFLICT ({pk}) DO UPDATE SET {update_str}
    """
    cur.execute(sql, values)
    return "UPSERT"


def ensure_target_schema(conn) -> None:
    """Cria uma tabela de controle de pipeline no target se não existir."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public._pipeline_metadata (
                topic       TEXT PRIMARY KEY,
                last_offset BIGINT,
                last_event  TIMESTAMPTZ DEFAULT NOW(),
                event_count BIGINT DEFAULT 0
            )
        """)
    conn.commit()
    logger.info("Schema de controle verificado.")


def update_metadata(cur, topic: str) -> None:
    cur.execute("""
        INSERT INTO public._pipeline_metadata (topic, last_event, event_count)
        VALUES (%s, NOW(), 1)
        ON CONFLICT (topic) DO UPDATE SET
            last_event  = NOW(),
            event_count = _pipeline_metadata.event_count + 1
    """, (topic,))


# ─── Loop Principal ───────────────────────────────────────────────────────────

def main() -> None:
    logger.info(f"Iniciando consumer → {KAFKA_BOOTSTRAP} / target: {TARGET_HOST}:{TARGET_PORT}/{TARGET_DB}")

    # Aguardar Kafka estar disponível
    for attempt in range(30):
        try:
            test_consumer = Consumer({
                "bootstrap.servers": KAFKA_BOOTSTRAP,
                "group.id": "health-check",
                "auto.offset.reset": "earliest",
            })
            test_consumer.list_topics(timeout=5)
            test_consumer.close()
            logger.info("Kafka disponível!")
            break
        except Exception as e:
            logger.info(f"Aguardando Kafka... ({attempt+1}/30): {e}")
            time.sleep(5)
    else:
        logger.error("Kafka não ficou disponível em 150s. Encerrando.")
        return

    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": "debezium-to-pg-v4",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
        "auto.commit.interval.ms": 1000,
        "session.timeout.ms": 30000,
        "heartbeat.interval.ms": 3000,
        "max.poll.interval.ms": 300000,
    })
    consumer.subscribe(TOPICS)

    conn = None
    stats = {t: 0 for t in TOPICS}
    last_log = time.time()

    try:
        conn = get_db_conn()
        ensure_target_schema(conn)

        logger.info(f"Subscrito em: {TOPICS}")
        logger.info("Aguardando eventos CDC...")

        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                # Log periódico de estatísticas
                if time.time() - last_log > 30:
                    total = sum(stats.values())
                    logger.info(f"Heartbeat — Total processado: {total} eventos | {stats}")
                    last_log = time.time()
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())

            topic   = msg.topic()
            value   = msg.value()
            if value is None:
                continue  # tombstone

            try:
                raw = json.loads(value.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Payload inválido no topic {topic}: {e}")
                continue

            # Debezium wraps in {schema: ..., payload: ...} even with schemas disabled
            # Extract the actual row data from 'payload' if present
            payload = raw.get("payload", raw) if isinstance(raw, dict) else raw

            # Skip null payloads (tombstones)
            if not payload:
                continue

            try:
                with conn.cursor() as cur:
                    op = upsert_row(cur, topic, coerce_payload(payload))
                    if op:
                        update_metadata(cur, topic)
                        stats[topic] = stats.get(topic, 0) + 1
                conn.commit()

                if sum(stats.values()) % 50 == 0:
                    logger.info(f"Processado: {stats}")

            except psycopg2.OperationalError:
                logger.warning("Reconectando ao target DB...")
                conn = get_db_conn()
            except Exception as e:
                logger.error(f"Erro ao processar evento [{topic}]: {e} | payload: {str(payload)[:200]}")
                conn.rollback()

    except KeyboardInterrupt:
        logger.info("Consumer encerrado pelo usuário.")
    finally:
        consumer.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
