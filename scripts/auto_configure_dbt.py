#!/usr/bin/env python3
"""
Auto-configurador do DBT - Engenharia de Dados Automatizada
===========================================================
Sistema inteligente que:
1. Detecta estado dos containers (Source/Target/Airbyte)
2. Testa conectividade dos bancos
3. Auto-configura DBT para o ambiente correto
4. Elimina configuração manual
"""

import subprocess
import psycopg2
import time
import os
import yaml
from pathlib import Path
from typing import Dict, Tuple, Optional

class DBTAutoConfigurator:
    def __init__(self):
        self.dbt_dir = Path.home() / ".dbt"
        self.profiles_file = self.dbt_dir / "profiles.yml"
        self.dbt_dir.mkdir(exist_ok=True)
        
        # Configurações de conexão
        self.source_config = {
            'host': 'localhost',
            'port': 5430,
            'user': 'admin',
            'password': 'admin',
            'database': 'db_source'
        }
        
        self.target_config = {
            'host': 'localhost', 
            'port': 5431,
            'user': 'admin',
            'password': 'admin',
            'database': 'db_target'
        }
    
    def log_info(self, msg: str):
        print(f"🤖 AUTO-CONFIG: {msg}")
    
    def log_success(self, msg: str):
        print(f"✅ {msg}")
    
    def log_warning(self, msg: str):
        print(f"⚠️  {msg}")
    
    def check_container_running(self, container_name: str) -> bool:
        """Verifica se container está rodando"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True, text=True
            )
            return container_name in result.stdout
        except:
            return False
    
    def test_postgres_connection(self, config: Dict) -> Tuple[bool, Optional[int]]:
        """Testa conexão PostgreSQL e retorna (success, record_count)"""
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                user=config['user'],
                password=config['password'],
                database=config['database'],
                connect_timeout=5
            )
            
            cursor = conn.cursor()
            # Verificar se tem dados
            try:
                cursor.execute("SELECT COUNT(*) FROM public.clientes")
                count = cursor.fetchone()[0]
                conn.close()
                return True, count
            except:
                conn.close()
                return True, 0
        except Exception as e:
            return False, None
    
    def detect_pipeline_state(self) -> str:
        """Detecta estado atual do pipeline"""
        self.log_info("Detectando estado do pipeline...")
        
        # Verificar containers
        source_running = self.check_container_running("postgres_source_db")
        target_running = self.check_container_running("postgres_target_db") 
        airbyte_running = self.check_container_running("airbyte_webapp")
        
        # Verificar conectividade
        source_ok, source_count = self.test_postgres_connection(self.source_config)
        target_ok, target_count = self.test_postgres_connection(self.target_config)
        
        self.log_info(f"Containers: Source({source_running}) Target({target_running}) Airbyte({airbyte_running})")
        self.log_info(f"Conectividade: Source({source_ok}:{source_count}) Target({target_ok}:{target_count})")
        
        # Lógica de decisão inteligente
        if target_ok and target_count and target_count > 0:
            return "PRODUCTION_CDC"  # Dados replicados via Airbyte
        elif source_ok and airbyte_running:
            return "AIRBYTE_READY"   # Airbyte pronto, aguardando replicação
        elif source_ok:
            return "DEVELOPMENT"     # Apenas Source disponível
        else:
            return "SETUP_REQUIRED"  # Nada configurado ainda
    
    def create_dbt_profile(self, state: str) -> Dict:
        """Cria configuração DBT baseada no estado detectado"""
        base_profile = {
            'type': 'postgres',
            'schema': 'public',  # Campo obrigatório!
            'threads': 4,
            'keepalives_idle': 0,
            'connect_timeout': 10,
            'search_path': 'public'
        }
        
        # Determinar qual banco usar baseado no estado
        if state == "PRODUCTION_CDC":
            # Usar Target - dados replicados pelo Airbyte
            config = {**base_profile, **self.target_config}
            source_database = 'db_target'  # Sources apontam para target
            self.log_success("Configurando DBT para TARGET (dados replicados CDC)")
            
        elif state in ["AIRBYTE_READY", "DEVELOPMENT"]:
            # Usar Source - desenvolvimento ou aguardando CDC
            config = {**base_profile, **self.source_config}
            source_database = 'db_source'  # Sources apontam para source
            self.log_success("Configurando DBT para SOURCE (desenvolvimento)")
            
        else:
            # Fallback para Source
            config = {**base_profile, **self.source_config}
            source_database = 'db_source'  # Sources apontam para source
            self.log_warning("Estado indefinido, usando SOURCE como fallback")
        
        # Adicionar variável para controlar database dos sources
        config['vars'] = {
            'source_database': source_database
        }
        
        return {
            'default': {
                'target': 'dev',
                'outputs': {
                    'dev': config
                }
            }
        }
    
    def write_profiles_yml(self, profile_config: Dict):
        """Escreve profiles.yml automaticamente"""
        with open(self.profiles_file, 'w') as f:
            yaml.dump(profile_config, f, default_flow_style=False, indent=2)
        
        self.log_success(f"profiles.yml auto-gerado: {self.profiles_file}")
    
    def verify_dbt_connection(self) -> bool:
        """Verifica se DBT está funcionando"""
        try:
            # Ir para diretório do projeto DBT
            project_dir = Path(__file__).parent.parent / "dbt_project"
            if not project_dir.exists():
                self.log_warning("Diretório dbt_project não encontrado")
                return False
            
            os.chdir(project_dir)
            
            # Testar conexão DBT
            result = subprocess.run(
                ["dbt", "debug", "--quiet"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            self.log_warning(f"Erro ao verificar DBT: {e}")
            return False
    
    def run_auto_configuration(self):
        """Executa configuração automática completa"""
        self.log_info("INICIANDO AUTO-CONFIGURAÇÃO INTELIGENTE DO DBT")
        self.log_info("=" * 60)
        
        # 1. Detectar estado
        state = self.detect_pipeline_state()
        self.log_info(f"Estado detectado: {state}")
        
        # 2. Criar configuração apropriada
        profile_config = self.create_dbt_profile(state)
        
        # 3. Escrever arquivo
        self.write_profiles_yml(profile_config)
        
        # 4. Verificar se funciona
        if self.verify_dbt_connection():
            self.log_success("🎉 DBT auto-configurado com sucesso!")
            return True
        else:
            self.log_warning("DBT configurado, mas conexão falhou")
            return False

def main():
    """Função principal"""
    configurator = DBTAutoConfigurator()
    success = configurator.run_auto_configuration()
    
    if success:
        print("\n🚀 SISTEMA TOTALMENTE AUTOMATIZADO!")
        print("   - Detecção automática de estado")
        print("   - Configuração dinâmica do DBT") 
        print("   - Zero intervenção manual necessária")
    else:
        print("\n⚠️  Configuração aplicada, verificar logs acima")
    
    return success

if __name__ == "__main__":
    main() 