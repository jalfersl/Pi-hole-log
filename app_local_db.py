#!/usr/bin/env python3
"""
Pi-hole Log Viewer com Banco Local
Versão otimizada que usa banco SQLite próprio para melhor performance
"""

from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import os
import json
import requests
import re
from datetime import datetime, timedelta
import subprocess
import paramiko
from config import FLASK_CONFIG, SSH_CONFIG

app = Flask(__name__)

# Configurações
ALERT_SETTINGS_FILE = 'alert_settings.json'
DATA_RETENTION_DAYS = 90  # Padrão: 90 dias

def load_alert_settings():
    """Carregar configurações de alerta"""
    if os.path.exists(ALERT_SETTINGS_FILE):
        with open(ALERT_SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            # Adicionar configuração de retenção se não existir
            if 'data_retention_days' not in settings:
                settings['data_retention_days'] = DATA_RETENTION_DAYS
            return settings
    return {
        'alerts_enabled': True,
        'ip_spike_threshold': 3.0,
        'domain_spike_threshold': 5.0,
        'network_spike_threshold': 2.5,
        'analysis_period_hours': 2,
        'telegram_enabled': False,
        'telegram_chat_id': '',
        'telegram_bot_token': '',
        'data_retention_days': DATA_RETENTION_DAYS,
        'pdf_title': 'Relatório de Logs do Pi-hole',
        'pdf_author': 'Pi-hole Log Viewer',
        'pdf_subject': 'Relatório de Logs'
    }

def save_alert_settings(settings):
    """Salvar configurações de alerta"""
    with open(ALERT_SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def send_telegram_notification(message):
    """Enviar notificação via Telegram"""
    settings = load_alert_settings()
    
    if not settings.get('telegramEnabled'):
        return False
    
    chat_id = settings.get('telegramChatId')
    bot_token = settings.get('telegramBotToken')
    
    if not chat_id or not bot_token:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': f"🚨 **Pi-hole Alert**\n\n{message}",
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, data=data, timeout=10)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('ok'):
            return True
        else:
            error_msg = response_data.get('description', 'Erro desconhecido')
            print(f"Erro Telegram API: {error_msg}")
            return False
    except Exception as e:
        print(f"Erro ao enviar notificação Telegram: {e}")
        return False

def check_all_alerts():
    """Verificar todos os alertas"""
    settings = load_alert_settings()
    
    if not settings.get('alerts_enabled'):
        return []
    
    alerts = []
    
    # Verificar picos de tráfego por IP
    try:
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        
        # Análise de picos por IP
        cursor.execute("""
            SELECT client, COUNT(*) as count
            FROM queries 
            WHERE timestamp >= datetime('now', '-2 hours')
            GROUP BY client
            ORDER BY count DESC
            LIMIT 10
        """)
        
        recent_ips = cursor.fetchall()
        
        if recent_ips:
            # Calcular média histórica
            cursor.execute("""
                SELECT client, AVG(count) as avg_count
                FROM (
                    SELECT client, COUNT(*) as count
                    FROM queries 
                    WHERE timestamp >= datetime('now', '-24 hours')
                    GROUP BY client, strftime('%H', timestamp)
                )
                GROUP BY client
            """)
            
            historical_avg = cursor.fetchall()
            avg_dict = {ip: avg for ip, avg in historical_avg}
            
            for ip, count in recent_ips:
                if ip in avg_dict and avg_dict[ip] > 0:
                    ratio = count / avg_dict[ip]
                    if ratio > settings.get('ip_spike_threshold', 3.0):
                        alerts.append({
                            'type': 'warning',
                            'severity': 'Médio',
                            'title': f'Pico de Tráfego - IP {ip}',
                            'message': f'IP {ip} apresentou {count} consultas nas últimas 2 horas (média: {avg_dict[ip]:.1f})',
                            'timestamp': datetime.now().isoformat()
                        })
        
        conn.close()
        
    except Exception as e:
        print(f"Erro ao verificar alertas: {e}")
    
    # Enviar notificações se houver alertas
    if alerts and settings.get('telegramEnabled'):
        for alert in alerts:
            send_telegram_notification(alert['message'])
    
    return alerts

@app.route('/')
def index():
    """Página principal - Dashboard"""
    return render_template('dashboard.html')

@app.route('/logs')
def logs():
    """Página de logs"""
    return render_template('logs.html')

@app.route('/config')
def config():
    """Página de configurações"""
    return render_template('config.html')

# API Routes
@app.route('/api/logs')
def api_logs():
    """API para buscar logs"""
    try:
        # Parâmetros da requisição
        ip_search = request.args.get('ip', '').strip()
        domain_search = request.args.get('domain', '').strip()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        start_time = request.args.get('start_time', '00:00')
        end_time = request.args.get('end_time', '23:59')
        lines = request.args.get('lines', 5000, type=int)
        
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        
        # Construir query para calcular tempo de atividade
        sql = """
            SELECT 
                domain,
                client,
                status,
                COUNT(*) as count,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen,
                ROUND((julianday(MAX(timestamp)) - julianday(MIN(timestamp))) * 24 * 60) as duration_minutes
            FROM queries 
            WHERE 1=1
        """
        params = []
        
        # Adicionar filtros
        if ip_search:
            sql += " AND client LIKE ?"
            params.append(f"%{ip_search}%")
        
        if domain_search:
            sql += " AND domain LIKE ?"
            params.append(f"%{domain_search}%")
        
        if start_date:
            start_datetime = f"{start_date} {start_time}"
            sql += " AND timestamp >= ?"
            params.append(start_datetime)
        
        if end_date:
            end_datetime = f"{end_date} {end_time}"
            sql += " AND timestamp <= ?"
            params.append(end_datetime)
        
        # Agrupar por domínio, IP e status
        sql += " GROUP BY domain, client, status"
        
        # Ordenar por contagem decrescente
        sql += " ORDER BY count DESC"
        
        # Limitar resultados
        sql += f" LIMIT {lines}"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        # Converter para formato esperado
        logs = []
        for row in rows:
            # Calcular tempo de atividade formatado
            duration_minutes = row[6] if row[6] else 0
            
            if duration_minutes == 0:
                activity_time = "Momentâneo"
            elif duration_minutes < 60:
                activity_time = f"{duration_minutes} min"
            elif duration_minutes < 1440:  # menos de 24 horas
                hours = duration_minutes // 60
                minutes = duration_minutes % 60
                activity_time = f"{hours}h {minutes}min"
            else:
                days = duration_minutes // 1440
                hours = (duration_minutes % 1440) // 60
                activity_time = f"{days}d {hours}h"
            
            log = {
                'domain': row[0],
                'ip': row[1],
                'status': row[2],
                'count': row[3],
                'timestamp': row[5],  # último acesso
                'activity_time': activity_time,
                'duration_minutes': duration_minutes
            }
            logs.append(log)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total_found': len(logs),
            'total_returned': len(logs),
            'limited': len(logs) >= lines
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stats')
def api_stats():
    """API para estatísticas do dashboard"""
    try:
        # Obter data da requisição
        selected_date = request.args.get('date')
        
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        
        # Construir filtro de data
        date_filter = ""
        if selected_date:
            date_filter = f"WHERE date(timestamp) = '{selected_date}'"
        else:
            # Se não foi especificada data, usar apenas o dia atual
            date_filter = "WHERE date(timestamp) = date('now')"
        
        # Total de consultas
        cursor.execute(f"SELECT COUNT(*) FROM queries {date_filter}")
        total_queries = cursor.fetchone()[0]
        
        # Consultas bloqueadas
        if selected_date:
            blocked_filter = f"WHERE date(timestamp) = '{selected_date}' AND status = 'blocked'"
        else:
            blocked_filter = "WHERE date(timestamp) = date('now') AND status = 'blocked'"
        cursor.execute(f"SELECT COUNT(*) FROM queries {blocked_filter}")
        blocked_queries = cursor.fetchone()[0]
        
        # Clientes únicos
        cursor.execute(f"SELECT COUNT(DISTINCT client) FROM queries {date_filter}")
        unique_clients = cursor.fetchone()[0]
        
        # Domínios únicos
        cursor.execute(f"SELECT COUNT(DISTINCT domain) FROM queries {date_filter}")
        unique_domains = cursor.fetchone()[0]
        
        # Taxa de bloqueio
        block_rate = (blocked_queries / total_queries * 100) if total_queries > 0 else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_queries': total_queries,
                'blocked_queries': blocked_queries,
                'unique_clients': unique_clients,
                'unique_domains': unique_domains,
                'block_rate': round(block_rate, 1)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/activity-chart')
def api_activity_chart():
    """API para gráfico de atividade"""
    try:
        # Obter data da requisição
        selected_date = request.args.get('date')
        
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        
        # Construir filtro de data
        if selected_date:
            date_filter = f"WHERE date(timestamp) = '{selected_date}'"
        else:
            # Se não foi especificada data, usar apenas o dia atual
            date_filter = "WHERE date(timestamp) = date('now')"
        
        # Dados por hora para a data selecionada
        cursor.execute(f"""
            SELECT 
                strftime('%H', timestamp) as hour,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked
            FROM queries 
            {date_filter}
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        """)
        
        data = cursor.fetchall()
        
        labels = [f"{hour}:00" for hour, _, _ in data]
        queries = [total for _, total, _ in data]
        blocked = [blocked for _, _, blocked in data]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'queries': queries,
                'blocked': blocked
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/top-domains')
def api_top_domains():
    """API para top domínios"""
    try:
        # Obter data da requisição
        selected_date = request.args.get('date')
        
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        
        # Construir filtro de data
        if selected_date:
            date_filter = f"WHERE date(timestamp) = '{selected_date}'"
        else:
            # Se não foi especificada data, usar apenas o dia atual
            date_filter = "WHERE date(timestamp) = date('now')"
        
        cursor.execute(f"""
            SELECT domain, COUNT(*) as count
            FROM queries 
            {date_filter}
            GROUP BY domain
            ORDER BY count DESC
            LIMIT 10
        """)
        
        domains = [{'domain': domain, 'count': count} for domain, count in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'domains': domains})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/top-blocked-domains')
def api_top_blocked_domains():
    """API para top domínios bloqueados"""
    try:
        # Obter data da requisição
        selected_date = request.args.get('date')
        
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        
        # Construir filtro de data
        if selected_date:
            date_filter = f"WHERE date(timestamp) = '{selected_date}' AND status = 'blocked'"
        else:
            # Se não foi especificada data, usar apenas o dia atual
            date_filter = "WHERE date(timestamp) = date('now') AND status = 'blocked'"
        
        cursor.execute(f"""
            SELECT domain, COUNT(*) as count
            FROM queries 
            {date_filter}
            GROUP BY domain
            ORDER BY count DESC
            LIMIT 10
        """)
        
        domains = [{'domain': domain, 'count': count} for domain, count in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'domains': domains})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/top-ips')
def api_top_ips():
    """API para top IPs"""
    try:
        # Obter data da requisição
        selected_date = request.args.get('date')
        
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        
        # Construir filtro de data
        if selected_date:
            date_filter = f"WHERE date(timestamp) = '{selected_date}' AND client != '127.0.0.1'"
        else:
            # Se não foi especificada data, usar apenas o dia atual
            date_filter = "WHERE date(timestamp) = date('now') AND client != '127.0.0.1'"
        
        cursor.execute(f"""
            SELECT client, COUNT(*) as count
            FROM queries 
            {date_filter}
            GROUP BY client
            ORDER BY count DESC
            LIMIT 10
        """)
        
        ips = [{'ip': ip, 'count': count} for ip, count in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'ips': ips})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recent-activity')
def api_recent_activity():
    """API para atividade recente"""
    try:
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, domain, client, status
            FROM queries 
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        
        activities = []
        for timestamp, domain, client, status in cursor.fetchall():
            activities.append({
                'timestamp': timestamp,
                'domain': domain,
                'ip': client,
                'status': 'blocked' if status == 'blocked' else 'allowed'
            })
        
        conn.close()
        
        return jsonify({'success': True, 'activities': activities})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/alerts')
def api_alerts():
    """API para alertas"""
    try:
        alerts = check_all_alerts()
        return jsonify({'success': True, 'alerts': alerts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/check-alerts')
def api_check_alerts():
    """API para verificar alertas"""
    try:
        alerts = check_all_alerts()
        return jsonify({'success': True, 'alerts': alerts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Configurações
@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """API para configurações"""
    if request.method == 'POST':
        try:
            data = request.json
            save_alert_settings(data)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    else:
        try:
            settings = load_alert_settings()
            return jsonify({'success': True, 'settings': settings})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test-notification')
def api_test_notification():
    """API para testar notificação"""
    try:
        settings = load_alert_settings()
        
        if not settings.get('telegramEnabled'):
            return jsonify({'success': False, 'error': 'Telegram não habilitado'})
        
        message = "🧪 **Teste de Notificação**\n\nEsta é uma notificação de teste do Pi-hole Log Viewer."
        
        if send_telegram_notification(message):
            return jsonify({'success': True, 'message': 'Notificação enviada com sucesso!'})
        else:
            return jsonify({'success': False, 'error': 'Bot foi bloqueado pelo usuário. Desbloqueie o bot no Telegram e tente novamente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/last-update')
def api_last_update():
    """API para obter a última atualização do Pi-hole"""
    try:
        # Verificar se existe arquivo de log de atualização
        log_file = 'auto_update.log'
        last_update = "Nunca"
        
        if os.path.exists(log_file):
            # Ler as últimas linhas do arquivo de log
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Procurar pela última linha de sucesso
            for line in reversed(lines):
                if '✅ Dados atualizados com sucesso!' in line:
                    # Extrair timestamp da linha
                    try:
                        timestamp_str = line.split(' - ')[0]
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                        last_update = timestamp.strftime('%d/%m/%Y, %H:%M:%S')
                    except:
                        # Se não conseguir parsear, usar a linha completa
                        last_update = line.strip()
                    break
                elif '🔄 Iniciando atualização automática' in line:
                    # Se encontrou início de atualização mas não sucesso, usar essa linha
                    try:
                        timestamp_str = line.split(' - ')[0]
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                        last_update = timestamp.strftime('%d/%m/%Y, %H:%M:%S') + ' (em andamento)'
                    except:
                        last_update = line.strip()
                    break
        
        return jsonify({
            'success': True,
            'last_update': last_update
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update-data')
def api_update_data():
    """API para atualizar dados do Pi-hole"""
    try:
        # Verificar se é primeira atualização (banco vazio)
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM queries")
        current_count = cursor.fetchone()[0]
        
        # Obter horário atual para limitar importação
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Se banco vazio, pegar dados até o horário atual
        if current_count == 0:
            print(f"🔄 Primeira atualização: Importando dados até {current_time}...")
            # Converter horário local para UTC para a query
            current_utc = (datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
            command = f"sqlite3 /etc/pihole/pihole-FTL.db 'SELECT datetime(timestamp, \"unixepoch\"), domain, client, status FROM queries WHERE datetime(timestamp, \"unixepoch\") <= \"{current_utc}\" ORDER BY timestamp DESC;'"
        else:
            # Pegar apenas registros mais recentes que o último no banco local, mas até o horário atual
            cursor.execute("SELECT MAX(timestamp) FROM queries")
            last_timestamp = cursor.fetchone()[0]
            if last_timestamp:
                print(f"🔄 Atualização incremental: Importando registros após {last_timestamp} até {current_time}...")
                # Converter horário local para UTC para a query
                current_utc = (datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
                command = f"sqlite3 /etc/pihole/pihole-FTL.db 'SELECT datetime(timestamp, \"unixepoch\"), domain, client, status FROM queries WHERE timestamp > (SELECT strftime(\"%s\", \"{last_timestamp}\")) AND datetime(timestamp, \"unixepoch\") <= \"{current_utc}\" ORDER BY timestamp DESC;'"
            else:
                print(f"🔄 Atualização: Importando dados das últimas 24 horas até {current_time}...")
                # Converter horário local para UTC para a query
                current_utc = (datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
                command = f"sqlite3 /etc/pihole/pihole-FTL.db 'SELECT datetime(timestamp, \"unixepoch\"), domain, client, status FROM queries WHERE timestamp >= strftime(\"%s\", \"now\", \"-24 hours\") AND datetime(timestamp, \"unixepoch\") <= \"{current_utc}\" ORDER BY timestamp DESC;'"
        
        conn.close()
        
        # Conectar ao servidor Pi-hole via SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        ssh.connect(
            SSH_CONFIG['host'],
            port=SSH_CONFIG.get('port', 22),
            username=SSH_CONFIG['username'],
            password=SSH_CONFIG['password']
        )
        
        # Executar comando para obter dados do Pi-hole FTL
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        ssh.close()
        
        if error:
            return jsonify({'success': False, 'error': f'Erro SSH: {error}'})
        
        # Processar dados e inserir no banco local
        conn = sqlite3.connect('pihole_logs.db')
        cursor = conn.cursor()
        
        # Carregar configurações
        settings = load_alert_settings()
        retention_days = settings.get('data_retention_days', DATA_RETENTION_DAYS)
        
        # Limpar dados antigos baseado na configuração
        cursor.execute(f"DELETE FROM queries WHERE timestamp < datetime('now', '-{retention_days} days')")
        
        # Inserir novos dados
        lines = output.strip().split('\n')
        inserted_count = 0
        skipped_future = 0
        
        print(f"🔄 Processando {len(lines)} linhas de dados...")
        
        for line in lines:
            if line.strip():
                try:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        timestamp, domain, client, status = parts[:4]
                        
                        # Verificar se o timestamp não é futuro
                        # Converter timestamp para datetime para comparação
                        try:
                            timestamp_dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                            current_dt = datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S')
                            
                            # O Pi-hole usa UTC, então precisamos converter para horário local
                            # Subtrair 3 horas para converter UTC para horário local (-03)
                            timestamp_local = timestamp_dt - timedelta(hours=3)
                            
                            # Verificar se o timestamp convertido não é futuro
                            if timestamp_local <= current_dt + timedelta(hours=1):
                                # Mapear status do Pi-hole para nosso formato
                                # Status 1 = bloqueado, outros = permitido
                                mapped_status = 'blocked' if status == '1' else 'allowed'
                                
                                # Inserir no banco local com timestamp convertido para horário local
                                local_timestamp = timestamp_local.strftime('%Y-%m-%d %H:%M:%S')
                                
                                cursor.execute("""
                                    INSERT OR IGNORE INTO queries (timestamp, domain, client, status)
                                    VALUES (?, ?, ?, ?)
                                """, (local_timestamp, domain, client, mapped_status))
                                inserted_count += 1
                                
                                if inserted_count % 1000 == 0:
                                    print(f"✅ Processados {inserted_count} registros...")
                            else:
                                skipped_future += 1
                                if skipped_future <= 5:  # Log apenas os primeiros 5
                                    print(f"⚠️ Ignorando registro futuro: {timestamp} (convertido: {local_timestamp}, atual: {current_time})")
                        except ValueError as e:
                            print(f"⚠️ Erro ao processar timestamp: {timestamp} - {e}")
                            continue
                except Exception as e:
                    print(f"Erro ao processar linha: {line} - {e}")
                    continue
        
        print(f"✅ Importação concluída: {inserted_count} inseridos, {skipped_future} futuros ignorados")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Dados atualizados com sucesso! {inserted_count} registros inseridos, {skipped_future} futuros ignorados.',
            'inserted_count': inserted_count,
            'skipped_future': skipped_future,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_records': current_count + inserted_count,
            'retention_days': retention_days,
            'current_time': current_time
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(**FLASK_CONFIG) 