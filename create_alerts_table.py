#!/usr/bin/env python3
"""
Script para criar tabela de alertas no banco de dados
"""

import sqlite3
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_alerts_table():
    """Cria a tabela de alertas"""
    try:
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        
        # Criar tabela alerts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL, -- 'ip_spike', 'domain_spike', 'network_spike'
                target TEXT NOT NULL, -- IP ou domínio
                current_count INTEGER NOT NULL,
                average_count INTEGER NOT NULL,
                threshold REAL NOT NULL,
                severity TEXT DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
                message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at DATETIME,
                resolved_by TEXT
            )
        ''')
        
        # Criar índices para performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_target ON alerts(target)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved)')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Tabela de alertas criada com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela de alertas: {e}")
        return False

def create_alert_settings_table():
    """Cria a tabela de configurações de alertas"""
    try:
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        
        # Criar tabela alert_settings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                description TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inserir configurações padrão
        default_settings = [
            ('ip_spike_threshold', '3.0', 'Multiplicador para alerta de pico por IP'),
            ('domain_spike_threshold', '5.0', 'Multiplicador para alerta de pico por domínio'),
            ('network_spike_threshold', '2.5', 'Multiplicador para alerta de pico na rede'),
            ('analysis_period_hours', '2', 'Período de análise em horas'),
            ('alerts_enabled', 'true', 'Habilitar/desabilitar alertas'),
            ('email_notifications', 'false', 'Notificações por email'),
            ('whatsapp_notifications', 'false', 'Notificações por WhatsApp')
        ]
        
        for key, value, description in default_settings:
            cursor.execute('''
                INSERT OR REPLACE INTO alert_settings (setting_key, setting_value, description)
                VALUES (?, ?, ?)
            ''', (key, value, description))
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Configurações de alertas criadas com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar configurações de alertas: {e}")
        return False

def main():
    """Função principal"""
    logger.info("🚨 Criando sistema de alertas...")
    
    # Criar tabela de alertas
    if create_alerts_table():
        logger.info("✅ Tabela de alertas criada")
    else:
        logger.error("❌ Falha ao criar tabela de alertas")
        return
    
    # Criar configurações de alertas
    if create_alert_settings_table():
        logger.info("✅ Configurações de alertas criadas")
    else:
        logger.error("❌ Falha ao criar configurações de alertas")
        return
    
    logger.info("🎉 Sistema de alertas criado com sucesso!")

if __name__ == "__main__":
    main() 