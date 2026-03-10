#!/usr/bin/env python3
"""
Pipeline Demo Loop - Kafka Architecture
Loop: Gera dados no Source → Kafka+Debezium replica automaticamente → dbt run
O consumidor Kafka cuida da replicação em tempo real; este script apenas
insere dados e dispara o dbt para atualizar a Gold layer.
"""

import subprocess
import time
import logging
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pipeline_loop")

INTERVAL      = int(sys.argv[1]) if len(sys.argv) > 1 else 15
DBT_CONTAINER = "dbt_runner_container"
DBT_PROJECT   = "/usr/app/dbt_project"
BASE_DIR      = "/Users/michaelsantos/Documents/GitHub/airbyte-dbt"


def gerar_dados() -> bool:
    result = subprocess.run(
        ["python3", "scripts/gerar_dados_continuos.py", "--once"],
        capture_output=True, text=True, timeout=30, cwd=BASE_DIR
    )
    if result.returncode == 0:
        logger.info(f"   Source: {result.stdout.strip()}")
        return True
    logger.warning(f"   Gerador falhou: {result.stderr[-150:]}")
    return False


def run_dbt() -> bool:
    result = subprocess.run(
        ["docker", "exec", DBT_CONTAINER, "bash", "-c",
         f"cd {DBT_PROJECT} && dbt run --profiles-dir /root/.dbt "
         f"--vars '{{source_database: db_target}}' --quiet 2>&1 | tail -3"],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0:
        logger.info(f"   dbt OK: {result.stdout.strip()}")
        return True
    logger.warning(f"   dbt falhou: {result.stdout[-200:]}")
    return False


def main():
    logger.info(f"Pipeline loop iniciado (ciclo={INTERVAL}s)")
    logger.info("O Kafka+Debezium replica dados automaticamente em tempo real.")

    ciclo = 0
    while True:
        ciclo += 1
        logger.info(f"\n{'='*44}")
        logger.info(f"  CICLO {ciclo} — {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'='*44}")

        logger.info("1. Gerando dados no Source...")
        gerar_dados()

        logger.info("2. dbt run (Gold layer)...")
        run_dbt()

        logger.info(f"Ciclo {ciclo} concluído. Kafka replicando em background. Próximo em {INTERVAL}s.\n")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
