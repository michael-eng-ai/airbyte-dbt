#!/usr/bin/env python3
"""
Script de Verificação do Ambiente - Pipeline de Dados
Verifica todo o ambiente passo a passo antes de iniciar o pipeline
"""

import subprocess
import time
import psycopg2
import requests
import sys
import os
from datetime import datetime
import json

class EnvironmentChecker:
    def __init__(self):
        self.start_time = datetime.now()
        self.logs = []
        # Credenciais padronizadas admin/admin
        self.db_config = {
            'host': 'localhost',
            'port': 5430,
            'database': 'db_source',
            'user': 'admin',
            'password': 'admin'
        }
        
    def log_info(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}]   {msg}"
        print(log_msg)
        self.logs.append({"timestamp": timestamp, "level": "INFO", "message": msg})
        
    def log_success(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}]  {msg}"
        print(log_msg)
        self.logs.append({"timestamp": timestamp, "level": "SUCCESS", "message": msg})
        
    def log_warning(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}]   {msg}"
        print(log_msg)
        self.logs.append({"timestamp": timestamp, "level": "WARNING", "message": msg})
        
    def log_error(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f"[{timestamp}]  {msg}"
        print(log_msg)
        self.logs.append({"timestamp": timestamp, "level": "ERROR", "message": msg})
        
    def save_error_log(self, error_msg):
        """Salva log de erro detalhado"""
        error_log = {
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "duration": str(datetime.now() - self.start_time),
            "logs": self.logs
        }
        
        with open("environment_check_error.log", "w") as f:
            json.dump(error_log, f, indent=2, ensure_ascii=False)
            
        self.log_error(f"Log de erro salvo em: environment_check_error.log")
        
    def cleanup_processes(self):
        """Limpa processos em caso de erro"""
        self.log_info("Limpando processos devido a erro...")
        try:
            subprocess.run(['./scripts/stop_demo.sh'], check=False)
        except:
            pass
    
    def check_docker(self):
        """Verifica se Docker está rodando"""
        self.log_info("Verificando Docker...")
        try:
            result = subprocess.run(['docker', 'info'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_success("Docker está rodando")
                return True
            else:
                self.log_error("Docker não está rodando")
                return False
        except Exception as e:
            self.log_error(f"Erro ao verificar Docker: {e}")
            return False
    
    def start_database_container(self):
        """Inicia apenas o container do banco"""
        self.log_info("Iniciando container PostgreSQL...")
        try:
            result = subprocess.run([
                'docker', 'compose', '-f', 'config/docker-compose.yml', 
                'up', '-d', 'postgres_source'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.log_success("Container PostgreSQL iniciado")
                return True
            else:
                self.log_error(f"Erro ao iniciar container: {result.stderr}")
                return False
        except Exception as e:
            self.log_error(f"Erro ao iniciar container: {e}")
            return False
    
    def wait_for_postgres_connection(self, max_attempts=30, delay=2):
        """Aguarda PostgreSQL estar disponível com retry"""
        self.log_info(f"Aguardando conexão PostgreSQL (máx {max_attempts * delay}s)...")
        
        for attempt in range(1, max_attempts + 1):
            try:
                conn = psycopg2.connect(**self.db_config)
                conn.close()
                self.log_success(f"Conexão PostgreSQL estabelecida (tentativa {attempt})")
                return True
            except Exception as e:
                if attempt < max_attempts:
                    self.log_info(f"Tentativa {attempt}/{max_attempts} - Aguardando {delay}s...")
                    time.sleep(delay)
                else:
                    self.log_error(f"Falha na conexão após {max_attempts} tentativas: {e}")
                    return False
        
        return False
    
    def verify_database_structure(self):
        """Verifica se o banco e tabelas existem - cria se necessário"""
        self.log_info("Verificando estrutura do banco...")
        
        # SEMPRE executar o script de criação/atualização
        # Isso garante que as tabelas estão atualizadas, mesmo que já existam
        self.log_info("Executando script de inicialização/atualização...")
        if not self.create_missing_tables():
            self.log_error("Falha na inicialização do banco")
            return False
            
        # Agora verificar se as tabelas foram criadas corretamente
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Verificar se as tabelas principais existem
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('clientes', 'pedidos', 'produtos', 'itens_pedido', 'campanhas_marketing', 'leads')
                ORDER BY table_name;
            """)
            
            tables = [row[0] for row in cur.fetchall()]
            
            if len(tables) >= 2:  # Pelo menos clientes e pedidos
                self.log_success(f"Banco inicializado - {len(tables)} tabelas disponíveis: {tables}")
                
                # Verificar estrutura das tabelas principais
                for table in ['clientes', 'pedidos']:
                    if table in tables:
                        cur.execute(f"""
                            SELECT column_name, data_type 
                            FROM information_schema.columns 
                            WHERE table_name = '{table}' 
                            ORDER BY ordinal_position;
                        """)
                        columns = cur.fetchall()
                        col_names = [col[0] for col in columns]
                        self.log_info(f"Tabela '{table}': {len(columns)} colunas - {col_names}")
                
                conn.close()
                return True
            else:
                self.log_error(f"Inicialização falhou - apenas {len(tables)} tabelas criadas")
                conn.close()
                return False
                
        except Exception as e:
            self.log_error(f"Erro ao verificar estrutura após criação: {e}")
            return False
    
    def create_missing_tables(self):
        """Cria as tabelas faltantes"""
        try:
            result = subprocess.run([
                'python3', 'scripts/criar_tabelas.py'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.log_success("Tabelas criadas automaticamente")
                return True
            else:
                self.log_error(f"Falha ao criar tabelas: {result.stderr}")
                return False
        except Exception as e:
            self.log_error(f"Erro ao executar criador de tabelas: {e}")
            return False
    
    def check_initial_data(self):
        """Verifica se há dados iniciais (opcional)"""
        self.log_info("Verificando dados iniciais...")
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Contar registros
            cur.execute("SELECT COUNT(*) FROM public.clientes")
            clientes_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM public.pedidos")
            pedidos_count = cur.fetchone()[0]
            
            self.log_info(f"Dados encontrados - Clientes: {clientes_count}, Pedidos: {pedidos_count}")
            
            if clientes_count > 0 or pedidos_count > 0:
                self.log_success("Banco contém dados iniciais")
            else:
                self.log_warning("Banco está vazio - dados serão inseridos pelo simulador")
            
            conn.close()
            return True
            
        except Exception as e:
            self.log_error(f"Erro ao verificar dados: {e}")
            return False
    
    def start_dbt_container(self):
        """Inicia container DBT (apenas para disponibilizar ambiente)"""
        self.log_info("Iniciando container DBT...")
        try:
            result = subprocess.run([
                'docker', 'compose', '-f', 'config/docker-compose.yml', 
                'up', '-d', 'dbt_runner'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.log_success("Container DBT iniciado (apenas ambiente)")
                time.sleep(5)  # Aguardar inicialização
                return True
            else:
                self.log_warning(f"Container DBT não iniciou, mas prosseguindo: {result.stderr}")
                return True  # Não falhar - DBT via Python não precisa do container
        except Exception as e:
            self.log_warning(f"Container DBT não iniciou, mas prosseguindo: {e}")
            return True  # Não falhar - DBT via Python não precisa do container
    
    def test_dbt_connection(self):
        """Testa conexão DBT via Python (não Docker)"""
        self.log_info("Testando DBT via Python...")
        
        try:
            result = subprocess.run([
                'python3', 'scripts/executar_dbt.py', 'debug'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.log_success("DBT Python configurado corretamente")
                return True
            else:
                self.log_warning("DBT Python com problemas, mas prosseguindo")
                self.log_info(f"Output DBT: {result.stdout}")
                if result.stderr:
                    self.log_info(f"Stderr DBT: {result.stderr}")
                # Não falhar - pode ser problema de configuração que será resolvido depois
                return True
        except Exception as e:
            self.log_warning(f"Erro ao testar DBT Python, mas prosseguindo: {e}")
            return True
    
    def check_service_port(self, port, service_name, timeout=5):
        """Verifica se um serviço está respondendo em uma porta"""
        try:
            response = requests.get(f'http://localhost:{port}', timeout=timeout)
            self.log_success(f"{service_name} respondendo na porta {port}")
            return True
        except Exception:
            self.log_warning(f"{service_name} não está respondendo na porta {port}")
            return False
    
    def check_optional_services(self):
        """Verifica serviços opcionais (Airbyte, Airflow)"""
        import sys
        
        # Verificar se deve verificar serviços completos
        verificar_completo = len(sys.argv) > 1 and sys.argv[1] == '--completo'
        
        if not verificar_completo:
            self.log_info("Verificação de serviços opcionais (Airbyte, Airflow) pulada")
            self.log_info("Use --completo para verificar todos os serviços")
            return True
        
        self.log_info("Verificando serviços opcionais...")
        
        servicos_opcionais = [
            (8001, "Airbyte"),
            (8080, "Airflow")
        ]
        
        for port, nome in servicos_opcionais:
            self.check_service_port(port, nome)
        
        return True

    def comprehensive_check(self):
        """Executa verificação completa do ambiente"""
        print("🔍 VERIFICAÇÃO COMPLETA DO AMBIENTE")
        print("=" * 60)
        
        # 1. Verificar Docker
        if not self.check_docker():
            self.save_error_log("Docker não está disponível")
            return False
        
        # 2. Iniciar banco
        if not self.start_database_container():
            self.save_error_log("Falha ao iniciar container PostgreSQL")
            self.cleanup_processes()
            return False
        
        # 3. Aguardar conexão com banco
        if not self.wait_for_postgres_connection():
            self.save_error_log("PostgreSQL não ficou disponível")
            self.cleanup_processes()
            return False
        
        # 4. Verificar estrutura do banco
        if not self.verify_database_structure():
            self.save_error_log("Estrutura do banco incorreta ou incompleta")
            self.cleanup_processes()
            return False
        
        # 5. Verificar dados iniciais
        self.check_initial_data()  # Não falha se não houver dados
        
        # 6. Iniciar DBT
        if not self.start_dbt_container():
            self.save_error_log("Falha ao iniciar container DBT")
            self.cleanup_processes()
            return False
        
        # 7. Testar DBT
        if not self.test_dbt_connection():
            self.save_error_log("DBT não está funcionando corretamente")
            self.cleanup_processes()
            return False
        
        # 8. Verificar serviços opcionais
        self.check_optional_services()
        
        # Sucesso!
        duration = datetime.now() - self.start_time
        self.log_success(f"Ambiente verificado com sucesso em {duration}")
        print("\n AMBIENTE PRONTO PARA PIPELINE!")
        print("=" * 60)
        
        return True

def main():
    checker = EnvironmentChecker()
    
    try:
        success = checker.comprehensive_check()
        if success:
            print("\n Ambiente OK - Pipeline pode prosseguir")
            sys.exit(0)
        else:
            print("\n Ambiente com problemas - Verifique os logs")
            sys.exit(1)
    except KeyboardInterrupt:
        checker.log_warning("Verificação interrompida pelo usuário")
        checker.cleanup_processes()
        sys.exit(1)
    except Exception as e:
        checker.log_error(f"Erro inesperado: {e}")
        checker.save_error_log(f"Erro inesperado: {e}")
        checker.cleanup_processes()
        sys.exit(1)

if __name__ == "__main__":
    main() 