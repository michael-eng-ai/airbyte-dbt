#!/usr/bin/env python3
"""
Script Orchestrador para Demonstração Completa
Gerencia todo o processo de apresentação do Pipeline de Dados
"""

import subprocess
import time
import sys
import signal
import os
from datetime import datetime

class DemoOrchestrator:
    def __init__(self):
        self.processos = []
        self.dashboard_processo = None
        self.insersor_processo = None
    
    def limpar_processos(self):
        """Limpa todos os processos em execução"""
        print("\n🧹 Limpando processos...")
        
        if self.dashboard_processo:
            self.dashboard_processo.terminate()
            print("   ✅ Dashboard parado")
        
        if self.insersor_processo:
            self.insersor_processo.terminate()
            print("   ✅ Insersor de dados parado")
        
        for processo in self.processos:
            try:
                processo.terminate()
            except:
                pass
    
    def verificar_dependencias(self):
        """Verifica se todas as dependências estão instaladas"""
        print("🔍 Verificando dependências...")
        
        try:
            import streamlit
            import plotly
            import psycopg2
            import pandas
            print("   ✅ Todas as dependências OK")
            return True
        except ImportError as e:
            print(f"   ❌ Dependência faltando: {e}")
            print("   💡 Execute: python3 -m pip install -r requirements.txt")
            return False
    
    def verificar_docker(self):
        """Verifica se o Docker está rodando"""
        print("🐳 Verificando Docker...")
        
        try:
            result = subprocess.run(['docker', 'compose', 'ps'], 
                                 capture_output=True, text=True)
            if 'postgres_source_db' in result.stdout:
                print("   ✅ PostgreSQL rodando")
                return True
            else:
                print("   ❌ PostgreSQL não encontrado")
                return False
        except:
            print("   ❌ Docker não encontrado")
            return False
    
    def executar_dbt(self):
        """Executa os modelos DBT"""
        print("🔧 Executando modelos DBT...")
        
        try:
            # Bronze
            subprocess.run([
                'docker', 'compose', 'exec', '-T', 'dbt_runner', 
                'dbt', 'run', '--select', 'tag:bronze'
            ], check=True)
            print("   ✅ Modelos Bronze executados")
            
            # Silver
            subprocess.run([
                'docker', 'compose', 'exec', '-T', 'dbt_runner', 
                'dbt', 'run', '--select', 'tag:silver'
            ], check=True)
            print("   ✅ Modelos Silver executados")
            
            return True
        except subprocess.CalledProcessError:
            print("   ❌ Erro ao executar DBT")
            return False
    
    def iniciar_dashboard(self):
        """Inicia o dashboard Streamlit"""
        print("📊 Iniciando dashboard...")
        
        try:
            self.dashboard_processo = subprocess.Popen([
                'streamlit', 'run', 'dashboard.py',
                '--server.port', '8501',
                '--server.address', 'localhost',
                '--server.headless', 'true'
            ])
            
            time.sleep(3)  # Aguarda inicialização
            print("   ✅ Dashboard disponível em: http://localhost:8501")
            return True
        except Exception as e:
            print(f"   ❌ Erro ao iniciar dashboard: {e}")
            return False
    
    def iniciar_insersor(self):
        """Inicia o script de inserção de dados"""
        print("📥 Iniciando simulador de dados...")
        
        try:
            self.insersor_processo = subprocess.Popen([
                'python3', 'insere_dados.py'
            ])
            
            time.sleep(2)
            print("   ✅ Simulador de dados ativo")
            return True
        except Exception as e:
            print(f"   ❌ Erro ao iniciar simulador: {e}")
            return False
    
    def mostrar_status(self):
        """Mostra o status atual da demonstração"""
        print("\n" + "="*60)
        print("🎬 DEMONSTRAÇÃO ATIVA - STATUS")
        print("="*60)
        print("📊 Dashboard: http://localhost:8501")
        print("📥 Dados sendo inseridos automaticamente")
        print("🔄 Pipeline DBT executado e funcionando")
        print("💾 PostgreSQL com dados em tempo real")
        print("="*60)
        print("⏱️  A demonstração continuará até você pressionar Ctrl+C")
        print("📈 Abra o dashboard para ver os gráficos sendo atualizados!")
        print("="*60)
    
    def executar_demonstracao(self):
        """Executa a demonstração completa"""
        print("🎬 INICIANDO DEMONSTRAÇÃO COMPLETA DO PIPELINE")
        print("=" * 60)
        print(f"⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Verificações
        if not self.verificar_dependencias():
            return False
        
        if not self.verificar_docker():
            print("💡 Execute primeiro: ./start_poc.sh basic")
            return False
        
        # Executar DBT
        if not self.executar_dbt():
            return False
        
        # Iniciar dashboard
        if not self.iniciar_dashboard():
            return False
        
        # Iniciar insersor de dados
        if not self.iniciar_insersor():
            return False
        
        # Mostrar status e aguardar
        self.mostrar_status()
        
        try:
            # Loop infinito - aguarda Ctrl+C
            while True:
                time.sleep(60)  # Atualiza status a cada minuto
                print(f"🔄 {datetime.now().strftime('%H:%M:%S')} - Demonstração ativa...")
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Demonstração finalizada pelo usuário")
            self.limpar_processos()
            return True
    
    def demo_rapida(self):
        """Versão rápida da demo - só visualiza dados existentes"""
        print("⚡ DEMO RÁPIDA - Visualização de Dados Existentes")
        print("=" * 60)
        
        if not self.verificar_dependencias():
            return False
        
        if not self.verificar_docker():
            print("💡 Execute primeiro: ./start_poc.sh basic")
            return False
        
        # Só executa DBT e mostra dados
        self.executar_dbt()
        
        print("\n📊 Executando visualização...")
        try:
            subprocess.run(['python3', 'visualizar_pipeline.py'], check=True)
        except subprocess.CalledProcessError:
            print("❌ Erro na visualização")
            return False
        
        print("\n✅ Demo rápida concluída!")
        return True

def signal_handler(sig, frame):
    """Handler para Ctrl+C"""
    print('\n⏹️  Encerrando demonstração...')
    sys.exit(0)

def main():
    # Registrar handler para Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    demo = DemoOrchestrator()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'rapida':
        demo.demo_rapida()
    else:
        demo.executar_demonstracao()

if __name__ == "__main__":
    main() 