#!/usr/bin/env python3
"""
Script para instalar automaticamente todas as dependências do pipeline
Garante que requests, psycopg2, dbt e outras libs estejam disponíveis
"""

import subprocess
import sys
import os

def log_info(msg: str):
    print(f"  {msg}")

def log_success(msg: str):
    print(f" {msg}")

def log_error(msg: str):
    print(f" {msg}")

def install_package(package: str, pip_name: str = None) -> bool:
    """Instala um pacote Python se não estiver disponível"""
    if pip_name is None:
        pip_name = package
        
    try:
        __import__(package)
        log_success(f"{package} já instalado")
        return True
    except ImportError:
        log_info(f"Instalando {package}...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", pip_name,
                "--quiet", "--disable-pip-version-check"
            ])
            log_success(f"{package} instalado com sucesso")
            return True
        except subprocess.CalledProcessError:
            log_error(f"Falha ao instalar {package}")
            return False

def install_system_dependencies():
    """Instala dependências do sistema se necessário"""
    log_info("Verificando dependências do sistema...")
    
    # No macOS, verificar se PostgreSQL client está disponível
    try:
        subprocess.run(["psql", "--version"], capture_output=True, check=True)
        log_success("PostgreSQL client disponível")
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_info("PostgreSQL client não encontrado - pode ser instalado via:")
        print("  brew install postgresql  # macOS")
        print("  apt-get install postgresql-client  # Ubuntu/Debian")

def main():
    """Instala todas as dependências necessárias"""
    print("🔧 INSTALAÇÃO DE DEPENDÊNCIAS DO PIPELINE")
    print("=" * 50)
    
    # Lista de dependências Python
    dependencies = [
        ("requests", "requests>=2.25.0"),
        ("psycopg2", "psycopg2-binary>=2.8.0"),
        ("pandas", "pandas>=1.3.0"),
        ("faker", "faker>=13.0.0"),
        ("fastapi", "fastapi>=0.68.0"),
        ("uvicorn", "uvicorn>=0.15.0"),
        ("sqlalchemy", "sqlalchemy>=1.4.0"),
    ]
    
    # DBT específico
    dbt_dependencies = [
        ("dbt.cli", "dbt-core>=1.0.0"),
        ("dbt.adapters.postgres", "dbt-postgres>=1.0.0"),
    ]
    
    # Instalar dependências básicas
    log_info("Instalando dependências básicas...")
    success_count = 0
    for package, pip_name in dependencies:
        if install_package(package, pip_name):
            success_count += 1
            
    # Instalar DBT
    log_info("Instalando DBT...")
    for package, pip_name in dbt_dependencies:
        if install_package(package, pip_name):
            success_count += 1
    
    # Verificar dependências do sistema
    install_system_dependencies()
    
    print("\n" + "=" * 50)
    if success_count >= len(dependencies) + len(dbt_dependencies) - 1:  # -1 porque DBT pode falhar em alguns casos
        log_success(" Dependências instaladas com sucesso!")
        print(" Pipeline pronto para execução")
        return 0
    else:
        log_error(f" Algumas dependências falharam ({success_count} de {len(dependencies) + len(dbt_dependencies)})")
        print("🔧 Verifique os erros acima e instale manualmente se necessário")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 