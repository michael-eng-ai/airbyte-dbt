#!/usr/bin/env python3
"""
Script para configuração automática do Airbyte via API
Elimina a necessidade de configuração manual na interface web
"""

import requests
import json
import time
import os
import sys
from typing import Dict, Any, Optional

# Configurações
AIRBYTE_API_URL = "http://localhost:8000/api/v1"
POSTGRES_SOURCE_HOST = "postgres_source"
POSTGRES_SOURCE_PORT = 5432
POSTGRES_SOURCE_DB = "db_source"
POSTGRES_SOURCE_USER = "admin"
POSTGRES_SOURCE_PASSWORD = "admin"

POSTGRES_TARGET_HOST = "postgres_target"
POSTGRES_TARGET_PORT = 5432
POSTGRES_TARGET_DB = "db_target"
POSTGRES_TARGET_USER = "admin"
POSTGRES_TARGET_PASSWORD = "admin"

# Tabelas para sincronizar
TABLES_TO_SYNC = ["clientes", "pedidos", "produtos", "leads"]

class AirbyteAutomator:
    def __init__(self):
        self.api_url = AIRBYTE_API_URL
        self.workspace_id = None
        self.source_id = None
        self.destination_id = None
        self.connection_id = None
        
    def log_info(self, msg: str):
        print(f"ℹ️  {msg}")
        
    def log_success(self, msg: str):
        print(f"✅ {msg}")
        
    def log_error(self, msg: str):
        print(f"❌ {msg}")
        
    def log_warning(self, msg: str):
        print(f"⚠️  {msg}")

    def wait_for_airbyte(self, max_attempts: int = 30) -> bool:
        """Aguarda Airbyte estar disponível"""
        self.log_info("Aguardando Airbyte estar disponível...")
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.api_url}/health", timeout=10)
                if response.status_code == 200:
                    self.log_success("Airbyte API disponível!")
                    return True
            except requests.exceptions.RequestException:
                pass
                
            self.log_info(f"Tentativa {attempt + 1}/{max_attempts} - aguardando 10s...")
            time.sleep(10)
            
        return False

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Faz requisição para API do Airbyte"""
        url = f"{self.api_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
                
            if response.status_code in [200, 201]:
                return response.json()
            else:
                self.log_error(f"Erro na API: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.log_error(f"Erro de conexão: {e}")
            return None

    def get_workspace(self) -> bool:
        """Obtém workspace padrão"""
        self.log_info("Obtendo workspace...")
        
        response = self.make_request("POST", "/workspaces/list")
        if not response or not response.get("workspaces"):
            self.log_error("Nenhum workspace encontrado")
            return False
            
        self.workspace_id = response["workspaces"][0]["workspaceId"]
        self.log_success(f"Workspace obtido: {self.workspace_id}")
        return True

    def create_postgres_source(self) -> bool:
        """Cria source PostgreSQL"""
        self.log_info("Criando source PostgreSQL...")
        
        source_definition_response = self.make_request("POST", "/source_definitions/list")
        if not source_definition_response:
            return False
            
        # Buscar definição do PostgreSQL
        postgres_definition = None
        for definition in source_definition_response.get("sourceDefinitions", []):
            if "postgres" in definition.get("name", "").lower():
                postgres_definition = definition
                break
                
        if not postgres_definition:
            self.log_error("Definição PostgreSQL não encontrada")
            return False
            
        source_data = {
            "workspaceId": self.workspace_id,
            "sourceDefinitionId": postgres_definition["sourceDefinitionId"],
            "connectionConfiguration": {
                "host": POSTGRES_SOURCE_HOST,
                "port": POSTGRES_SOURCE_PORT,
                "database": POSTGRES_SOURCE_DB,
                "username": POSTGRES_SOURCE_USER,
                "password": POSTGRES_SOURCE_PASSWORD,
                "ssl": False,
                "replication_method": {
                    "method": "CDC",
                    "plugin": "pgoutput",
                    "publication": "airbyte_publication",
                    "replication_slot": "airbyte_slot"
                }
            },
            "name": "PostgreSQL Source - CDC"
        }
        
        response = self.make_request("POST", "/sources/create", source_data)
        if not response:
            return False
            
        self.source_id = response["sourceId"]
        self.log_success(f"Source criado: {self.source_id}")
        return True

    def create_postgres_destination(self) -> bool:
        """Cria destination PostgreSQL"""
        self.log_info("Criando destination PostgreSQL...")
        
        dest_definition_response = self.make_request("POST", "/destination_definitions/list")
        if not dest_definition_response:
            return False
            
        # Buscar definição do PostgreSQL
        postgres_definition = None
        for definition in dest_definition_response.get("destinationDefinitions", []):
            if "postgres" in definition.get("name", "").lower():
                postgres_definition = definition
                break
                
        if not postgres_definition:
            self.log_error("Definição PostgreSQL destination não encontrada")
            return False
            
        destination_data = {
            "workspaceId": self.workspace_id,
            "destinationDefinitionId": postgres_definition["destinationDefinitionId"],
            "connectionConfiguration": {
                "host": POSTGRES_TARGET_HOST,
                "port": POSTGRES_TARGET_PORT,
                "database": POSTGRES_TARGET_DB,
                "username": POSTGRES_TARGET_USER,
                "password": POSTGRES_TARGET_PASSWORD,
                "ssl": False,
                "schema": "public"
            },
            "name": "PostgreSQL Target - CDC"
        }
        
        response = self.make_request("POST", "/destinations/create", destination_data)
        if not response:
            return False
            
        self.destination_id = response["destinationId"]
        self.log_success(f"Destination criado: {self.destination_id}")
        return True

    def discover_schema(self) -> Optional[Dict]:
        """Descobre schema do source"""
        self.log_info("Descobrindo schema...")
        
        discover_data = {
            "sourceId": self.source_id,
            "disable_cache": True
        }
        
        response = self.make_request("POST", "/sources/discover_schema", discover_data)
        if not response:
            return None
            
        self.log_success("Schema descoberto com sucesso")
        return response.get("catalog")

    def create_connection(self, catalog: Dict) -> bool:
        """Cria conexão com sincronização das tabelas especificadas"""
        self.log_info("Criando conexão...")
        
        # Configurar streams para as tabelas desejadas
        streams = []
        for stream in catalog.get("streams", []):
            stream_name = stream.get("stream", {}).get("name", "")
            
            if stream_name in TABLES_TO_SYNC:
                # Configurar para Full Refresh + Overwrite (mais simples para CDC)
                configured_stream = {
                    "stream": stream["stream"],
                    "config": {
                        "selected": True,
                        "syncMode": "full_refresh",
                        "destinationSyncMode": "overwrite",
                        "primaryKey": [["id"]] if "id" in str(stream.get("stream", {})) else [],
                        "cursorField": []
                    }
                }
                streams.append(configured_stream)
                self.log_info(f"Configurando tabela: {stream_name}")
        
        if not streams:
            self.log_error("Nenhuma tabela configurada para sincronização")
            return False
            
        connection_data = {
            "sourceId": self.source_id,
            "destinationId": self.destination_id,
            "syncCatalog": {
                "streams": streams
            },
            "schedule": {
                "scheduleType": "manual"  # Sincronização manual para controle
            },
            "status": "active",
            "name": "PostgreSQL CDC Connection"
        }
        
        response = self.make_request("POST", "/connections/create", connection_data)
        if not response:
            return False
            
        self.connection_id = response["connectionId"]
        self.log_success(f"Conexão criada: {self.connection_id}")
        return True

    def trigger_sync(self) -> bool:
        """Dispara sincronização inicial"""
        self.log_info("Disparando sincronização inicial...")
        
        sync_data = {
            "connectionId": self.connection_id
        }
        
        response = self.make_request("POST", "/connections/sync", sync_data)
        if not response:
            return False
            
        job_id = response.get("job", {}).get("id")
        self.log_success(f"Sincronização iniciada - Job ID: {job_id}")
        
        # Aguardar conclusão da sincronização
        return self.wait_for_sync_completion(job_id)

    def wait_for_sync_completion(self, job_id: str, max_attempts: int = 30) -> bool:
        """Aguarda conclusão da sincronização"""
        self.log_info("Aguardando conclusão da sincronização...")
        
        for attempt in range(max_attempts):
            job_data = {"id": job_id}
            response = self.make_request("POST", "/jobs/get", job_data)
            
            if response:
                status = response.get("job", {}).get("status")
                
                if status == "succeeded":
                    self.log_success("Sincronização concluída com sucesso!")
                    return True
                elif status == "failed":
                    self.log_error("Sincronização falhou!")
                    return False
                elif status in ["running", "pending"]:
                    self.log_info(f"Sincronização em andamento... ({attempt + 1}/{max_attempts})")
                    time.sleep(10)
                else:
                    self.log_warning(f"Status desconhecido: {status}")
                    time.sleep(10)
            else:
                time.sleep(10)
                
        self.log_error("Timeout aguardando sincronização")
        return False

    def setup_complete_pipeline(self) -> bool:
        """Executa configuração completa do pipeline"""
        self.log_info("🚀 INICIANDO CONFIGURAÇÃO AUTOMÁTICA DO AIRBYTE")
        print("=" * 50)
        
        # 1. Aguardar Airbyte disponível
        if not self.wait_for_airbyte():
            self.log_error("Airbyte não disponível")
            return False
            
        # 2. Obter workspace
        if not self.get_workspace():
            return False
            
        # 3. Criar source
        if not self.create_postgres_source():
            return False
            
        # 4. Criar destination
        if not self.create_postgres_destination():
            return False
            
        # 5. Descobrir schema
        catalog = self.discover_schema()
        if not catalog:
            return False
            
        # 6. Criar conexão
        if not self.create_connection(catalog):
            return False
            
        # 7. Disparar sincronização inicial
        if not self.trigger_sync():
            return False
            
        self.log_success("🎉 CONFIGURAÇÃO AUTOMÁTICA CONCLUÍDA!")
        print("=" * 50)
        self.log_info(f"📊 Connection ID: {self.connection_id}")
        self.log_info("🌐 Acesse http://localhost:8001 para monitorar")
        
        return True

def main():
    """Função principal"""
    automator = AirbyteAutomator()
    
    if automator.setup_complete_pipeline():
        print("\n✅ Pipeline CDC configurado automaticamente!")
        print("🔄 Dados sendo sincronizados do Source para Target")
        print("🛠️ Agora execute: python3 scripts/executar_dbt.py full")
        return 0
    else:
        print("\n❌ Falha na configuração automática do Airbyte")
        print("🔧 Verificar logs acima e configurar manualmente se necessário")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 