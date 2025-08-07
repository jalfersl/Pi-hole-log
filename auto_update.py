#!/usr/bin/env python3
"""
Script de Atualização Automática do Pi-hole Log Viewer
"""

import time
import schedule
import logging
import requests
import subprocess
import os
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def update_pihole_data():
    """Atualiza os dados do Pi-hole"""
    try:
        logger.info("🔄 Iniciando atualização automática dos dados...")
        
        # Chamar o endpoint de atualização da aplicação
        response = requests.get('http://localhost:8082/api/update-data', timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                logger.info("✅ Dados atualizados com sucesso!")
            else:
                logger.error(f"❌ Erro na atualização: {data.get('error', 'Erro desconhecido')}")
        else:
            logger.error(f"❌ Erro HTTP {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Não foi possível conectar à aplicação (porta 8081)")
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout na atualização")
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")

def check_application_status():
    """Verifica se a aplicação está rodando"""
    try:
        response = requests.get('http://localhost:8082/api/stats', timeout=5)
        return response.status_code == 200
    except:
        return False

def start_application():
    """Inicia a aplicação se não estiver rodando"""
    try:
        # Verificar se a aplicação está rodando
        if not check_application_status():
            logger.info("🚀 Iniciando aplicação...")
            
            # Mudar para o diretório da aplicação
            os.chdir('/home/server-rede/pihole-log-viewer')
            
            # Ativar ambiente virtual
            activate_cmd = "source venv/bin/activate"
            
            # Iniciar aplicação em background
            start_cmd = f"{activate_cmd} && nohup python3 app_local_db.py > app.log 2>&1 &"
            
            subprocess.run(start_cmd, shell=True, check=True)
            
            # Aguardar um pouco para a aplicação inicializar
            time.sleep(10)
            
            if check_application_status():
                logger.info("✅ Aplicação iniciada com sucesso!")
            else:
                logger.error("❌ Falha ao iniciar aplicação")
        else:
            logger.info("✅ Aplicação já está rodando")
            
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar aplicação: {e}")

def get_update_interval():
    """Lê o intervalo de atualização da configuração"""
    try:
        # Tentar ler da configuração via API
        response = requests.get('http://localhost:8082/api/config', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and 'settings' in data:
                interval = data['settings'].get('updateInterval', '30')
                return int(interval)
    except:
        pass
    
    # Valor padrão se não conseguir ler
    return 30

def main():
    """Função principal"""
    logger.info("🚀 Iniciando Script de Atualização Automática")
    
    # Verificar se estamos no diretório correto
    if not os.path.exists('app_local_db.py'):
        logger.error("❌ Script deve ser executado no diretório da aplicação")
        return
    
    # Iniciar aplicação se necessário
    start_application()
    
    # Obter intervalo de atualização
    interval = get_update_interval()
    logger.info(f"⏰ Atualizações a cada {interval} minutos")
    
    # Agendar atualizações
    schedule.every(interval).minutes.do(update_pihole_data)
    
    # Executar primeira atualização imediatamente
    logger.info("🔄 Executando primeira atualização...")
    update_pihole_data()
    
    # Loop principal
    logger.info("⏰ Aguardando próximas atualizações...")
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto
            
        except KeyboardInterrupt:
            logger.info("🛑 Script interrompido pelo usuário")
            break
        except Exception as e:
            logger.error(f"❌ Erro no loop principal: {e}")
            time.sleep(60)  # Aguardar antes de tentar novamente

if __name__ == "__main__":
    main() 