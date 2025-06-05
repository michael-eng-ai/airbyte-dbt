from __future__ import annotations

import pendulum
import os
from pathlib import Path

from airflow.models.dag import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.hooks.base import BaseHook
from airflow.utils.trigger_rule import TriggerRule

import json
import logging

# Função de callback para falhas
def task_failure_alert(context):
    logging.error(f"Task {context['task_instance_key_str']} failed.")
    # Aqui você pode adicionar integrações com Slack, Email, etc.
    # Exemplo: send_slack_notification(f"Task {context['task_instance_key_str']} failed.")

# Configurações de rede e caminhos em ambiente Docker
NETWORK_MODE = os.environ.get("DOCKER_NETWORK", "airbyte-dbt_default")
DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt_project")

# Configurações do Airbyte - será configurado via interface do Airflow
AIRBYTE_HOST = os.environ.get("AIRBYTE_HOST", "airbyte-server")
AIRBYTE_PORT = os.environ.get("AIRBYTE_PORT", "8000")
AIRBYTE_API_URL = f"http://{AIRBYTE_HOST}:{AIRBYTE_PORT}/api/v1"

# Timeout para sincronização do Airbyte (em segundos)
AIRBYTE_SYNC_TIMEOUT = int(os.environ.get("AIRBYTE_SYNC_TIMEOUT", "3600"))

# Credenciais do banco de dados
DB_HOST = os.environ.get("DB_HOST", "postgres_source_db")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "admin")
DB_NAME = os.environ.get("DB_NAME", "db_source")

with DAG(
    dag_id="pipeline_dados_riocard_cdc",
    start_date=pendulum.datetime(2025, 5, 7, tz="UTC"),
    catchup=False,
    schedule_interval="@daily",
    tags=["dados", "riocard", "cdc", "airbyte", "dbt"],
    default_args={
        'on_failure_callback': task_failure_alert,
    },
    doc_md="""
    ### Pipeline de Dados Riocard com CDC, Airbyte e dbt

    Este DAG orquestra o pipeline de dados completo:
    1.  **Popula/Atualiza Banco de Origem**: Executa um script Python para inserir ou atualizar dados no banco PostgreSQL de origem, simulando transações.
    2.  **Sincronização Airbyte**: Dispara uma sincronização no Airbyte para replicar os dados (incluindo as alterações capturadas por CDC).
    3.  **Transformações dbt**: Executa os modelos dbt para transformar os dados brutos nas camadas Bronze, Silver e Gold.
    
    **Configuração:**
    - Para o Airbyte, você precisará criar uma conexão e obter o connection_id para configurar na variável AIRBYTE_CONNECTION_ID do Airflow.
    - Esse DAG está configurado para usar o ambiente Docker integrado.
    """
) as dag:

    # Task 1: Popular/Atualizar o banco de dados de origem
    populate_source_db = BashOperator(
        task_id="popular_banco_origem",
        bash_command="cd /app/scripts && python populate_db.py",
        env={
            'DB_HOST': DB_HOST,
            'DB_NAME': DB_NAME,
            'DB_USER': DB_USER,
            'DB_PASSWORD': DB_PASSWORD,
            'DB_PORT': DB_PORT
        },
        doc_md="""
        #### Task: Popular Banco de Origem
        Executa o script `populate_db.py` para inserir, atualizar e excluir dados fictícios
        no banco de dados PostgreSQL de origem para testar o CDC.
        """
    )

    # Task 3: Disparar a sincronização do Airbyte via API HTTP
    # Task 2: Disparar a sincronização do Airbyte via API HTTP
    trigger_airbyte_sync = SimpleHttpOperator(
        task_id="disparar_sync_airbyte",
        http_conn_id='airbyte_conn', # Certifique-se que esta conexão aponta para a API do Airbyte
        endpoint='/connections/sync',
        method='POST',
        data=json.dumps({"connectionId": Variable.get("AIRBYTE_CONNECTION_ID")}),
        headers={"Content-Type": "application/json"},
        response_check=lambda response: response.status_code == 200 and response.json().get('jobInfo', {}).get('job', {}).get('status') == 'succeeded',
        log_response=True,
        execution_timeout=pendulum.duration(seconds=AIRBYTE_SYNC_TIMEOUT), # Adicionar timeout para a task
        doc_md="""
        #### Task: Disparar Sincronização Airbyte
        Dispara a sincronização da conexão Airbyte especificada pela variável `AIRBYTE_CONNECTION_ID`.
        Certifique-se de que a variável `AIRBYTE_CONNECTION_ID` está configurada no Airflow.
        """
    )

    # Task 3: Executar transformações dbt
    run_dbt_models = BashOperator(
        task_id="executar_modelos_dbt",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run --profiles-dir /root/.dbt",
        env={
            'DBT_DB_HOST': DB_HOST,
            'DBT_DB_NAME': DB_NAME,
            'DBT_DB_USER': DB_USER,
            'DBT_DB_PASSWORD': DB_PASSWORD,
            'DBT_DB_PORT': DB_PORT
        },
        doc_md="""
        #### Task: Executar Modelos dbt
        Executa os modelos dbt para transformar os dados nas camadas Bronze, Silver e Gold.
        """
    )

    # Task 4: Executar testes dbt
    run_dbt_tests = BashOperator(
        task_id="testar_modelos_dbt",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt test --profiles-dir /root/.dbt",
        env={
            'DBT_DB_HOST': DB_HOST,
            'DBT_DB_NAME': DB_NAME,
            'DBT_DB_USER': DB_USER,
            'DBT_DB_PASSWORD': DB_PASSWORD,
            'DBT_DB_PORT': DB_PORT
        },
        doc_md="""
        #### Task: Testar Modelos dbt
        Executa os testes definidos no projeto dbt para validar a qualidade dos dados.
        """
    )

    # Definindo as dependências entre as tasks
    populate_source_db >> trigger_airbyte_sync >> run_dbt_models >> run_dbt_tests