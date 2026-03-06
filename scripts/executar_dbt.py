#!/usr/bin/env python3
"""
Script Python para executar DBT localmente
Trabalha em conjunto com o auto-configurador inteligente
"""

import subprocess
import sys
import os
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s : %(message)s')
logger = logging.getLogger("executor_dbt")

def log_info(msg: str) -> None:
    logger.info(msg)

def log_success(msg: str) -> None:
    logger.info(f"SUCCESS: {msg}")

def log_error(msg: str) -> None:
    logger.error(msg)

def log_warning(msg: str) -> None:
    logger.warning(msg)

def ensure_dbt_installed() -> bool:
    """Verifica se DBT está instalado"""
    try:
        result = subprocess.run(["dbt", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            log_success("DBT já está instalado")
            return True
    except FileNotFoundError:
        pass
    
    log_info("Instalando DBT...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "dbt-postgres>=1.0.0", "dbt-core>=1.0.0",
            "--quiet", "--disable-pip-version-check"
        ])
        log_success("DBT instalado com sucesso")
        return True
    except subprocess.CalledProcessError:
        log_error("Falha ao instalar DBT")
        return False

def check_profiles_yml():
    """Verifica se profiles.yml existe (criado pelo auto-configurador)"""
    dbt_dir = Path.home() / ".dbt"
    profiles_file = dbt_dir / "profiles.yml"
    
    if profiles_file.exists():
        log_success(f"profiles.yml encontrado em {profiles_file}")
        return True
    else:
        log_warning("profiles.yml não encontrado!")
        log_info("Execute primeiro: python3 scripts/auto_configure_dbt.py")
        return False

def run_dbt_command(command: str):
    """Executa comando DBT no diretório correto"""
    
    # Garantir que estamos no diretório do projeto DBT
    project_dir = Path(__file__).parent.parent / "dbt_project"
    
    if not project_dir.exists():
        log_error(f"Diretório do projeto DBT não encontrado: {project_dir}")
        return False
    
    # Mudar para o diretório do projeto
    original_dir = os.getcwd()
    os.chdir(project_dir)
    
    try:
        if command == "debug":
            log_info("Executando dbt debug...")
            result = subprocess.run(["dbt", "debug"], capture_output=True, text=True)
            
        elif command == "full":
            log_info("Executando pipeline DBT completo...")
            # Primeiro run dos modelos
            result = subprocess.run(["dbt", "run"], capture_output=True, text=True)
            if result.returncode == 0:
                log_success("Modelos executados com sucesso")
                # Depois testes
                log_info("Executando testes...")
                result = subprocess.run(["dbt", "test"], capture_output=True, text=True)
            
        elif command == "test":
            log_info("Executando testes DBT...")
            result = subprocess.run(["dbt", "test"], capture_output=True, text=True)
            
        elif command == "run":
            log_info("Executando modelos DBT...")
            result = subprocess.run(["dbt", "run"], capture_output=True, text=True)
            
        elif command == "deps":
            log_info("Instalando dependências DBT...")
            result = subprocess.run(["dbt", "deps"], capture_output=True, text=True)
            
        else:
            log_error(f"Comando não reconhecido: {command}")
            return False
        
        # Mostrar output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
            
        if result.returncode == 0:
            log_success(f"Comando dbt {command} executado com sucesso!")
            return True
        else:
            log_error(f"Comando dbt {command} falhou!")
            return False
            
    except FileNotFoundError:
        log_error("DBT não encontrado. Instalando...")
        if ensure_dbt_installed():
            return run_dbt_command(command)  # Tentar novamente
        return False
    except Exception as e:
        log_error(f"Erro ao executar dbt: {e}")
        return False
    finally:
        os.chdir(original_dir)

def auto_configure_if_needed():
    """Executa auto-configurador se necessário"""
    log_info("Verificando configuração DBT...")
    
    # Executar auto-configurador
    auto_config_path = Path(__file__).parent / "auto_configure_dbt.py"
    if auto_config_path.exists():
        try:
            result = subprocess.run([sys.executable, str(auto_config_path)], 
                                    capture_output=True, text=True)
            if result.returncode == 0:
                log_success("Auto-configuração executada com sucesso")
                return True
            else:
                log_warning("Auto-configuração falhou")
                if result.stderr:
                    print(result.stderr)
                return False
        except Exception as e:
            log_error(f"Erro ao executar auto-configurador: {e}")
            return False
    else:
        log_error("Auto-configurador não encontrado")
        return False

def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python3 executar_dbt.py <comando>")
        print("Comandos disponíveis:")
        print("  debug    - Verificar configuração DBT")
        print("  run      - Executar modelos")
        print("  test     - Executar testes")
        print("  full     - Executar modelos + testes")
        print("  deps     - Instalar dependências")
        print("  auto     - Executar auto-configurador")
        return 1
    
    comando = sys.argv[1]
    
    logger.info(" EXECUTOR DBT PYTHON")
    logger.info("=" * 40)
    
    # Garantir que DBT está instalado
    if not ensure_dbt_installed():
        return 1
    
    # Comando especial para auto-configurar
    if comando == "auto":
        if auto_configure_if_needed():
            log_info("Auto-configuração concluída. Execute agora: python3 scripts/executar_dbt.py run")
        return 0
    
    # Verificar se profiles.yml existe
    if not check_profiles_yml():
        log_info("Executando auto-configurador...")
        if not auto_configure_if_needed():
            log_error("Falha na auto-configuração. Configure manualmente ou verifique os logs.")
            return 1
    
    # Executar comando DBT
    if run_dbt_command(comando):
        log_success(" Execução DBT concluída!")
        return 0
    else:
        log_error(" Falha na execução DBT!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 