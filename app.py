import sqlite3
import tempfile
import os
from flask import Flask, render_template, request, jsonify
import re
import paramiko
from datetime import datetime, timedelta
import logging
from config import SSH_CONFIG, FLASK_CONFIG, LOGGING_CONFIG, FILTER_CONFIG

app = Flask(__name__)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"]
)
logger = logging.getLogger(__name__)

def fetch_remote_log_tail(ip=None, user=None, password=None, remote_path=None, lines=1000):
    """Busca apenas as últimas linhas do log remoto via SSH"""
    # Usar configurações padrão se não fornecidas
    ip = ip or SSH_CONFIG["host"]
    user = user or SSH_CONFIG["username"]
    password = password or SSH_CONFIG["password"]
    remote_path = remote_path or SSH_CONFIG["log_path"]
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            ip, 
            username=user, 
            password=password, 
            timeout=SSH_CONFIG["timeout"]
        )

        # Usar tail para pegar apenas as últimas linhas
        command = f"tail -n {lines} {remote_path}"
        stdin, stdout, stderr = ssh.exec_command(command)
        content = stdout.read().decode("utf-8").splitlines()
        ssh.close()
        
        logger.info(f"✅ Últimas {len(content)} linhas carregadas com sucesso")
        return content
    except Exception as e:
        logger.error(f"❌ Erro ao conectar via SSH: {e}")
        raise

def fetch_remote_log_by_date(ip=None, user=None, password=None, remote_path=None, start_date=None, end_date=None):
    """Busca logs por período de data - versão que busca em todo o arquivo"""
    ip = ip or SSH_CONFIG["host"]
    user = user or SSH_CONFIG["username"]
    password = password or SSH_CONFIG["password"]
    remote_path = remote_path or SSH_CONFIG["log_path"]
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            ip, 
            username=user, 
            password=password, 
            timeout=SSH_CONFIG["timeout"]
        )

        # Buscar em TODO o arquivo quando há filtros
        command = f"cat {remote_path}"
        logger.info(f" Buscando em TODO o arquivo (filtros aplicados)")
        
        stdin, stdout, stderr = ssh.exec_command(command)
        content = stdout.read().decode("utf-8").splitlines()
        ssh.close()
        
        logger.info(f"✅ Logs carregados: {len(content)} linhas")
        return content
    except Exception as e:
        logger.error(f"❌ Erro ao buscar logs por data: {e}")
        raise

def fetch_remote_log(ip=None, user=None, password=None, remote_path=None):
    """Busca logs remotos via SSH (método original para compatibilidade)"""
    return fetch_remote_log_tail(ip, user, password, remote_path, 1000)

def parse_log_line(line):
    """Parse de uma linha de log do Pi-hole - versão que filtra consultas internas e cache"""
    # Padrão melhorado para capturar mais informações
    patterns = [
        # Padrão para logs de query com IP
        r"^(\w+\s+\d+\s+\d+:\d+:\d+).*?query\[(.*?)\]\s+(.*?)\s+from\s+(.*?)$",
        # Padrão para logs de query sem IP (apenas domínio)
        r"^(\w+\s+\d+\s+\d+:\d+:\d+).*?query\[(.*?)\]\s+(.*?)$",
        # Padrão para logs de forwarded
        r"^(\w+\s+\d+\s+\d+:\d+:\d+).*?forwarded\s+(.*?)\s+to\s+(.*?)$",
        # Padrão para logs de cached-stale
        r"^(\w+\s+\d+\s+\d+:\d+:\d+).*?cached-stale\s+(.*?)\s+is\s+(.*?)$"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            timestamp = match.group(1)
            
            # Determinar o tipo de log baseado no padrão
            if "query[" in line:
                query_type = match.group(2)
                domain = match.group(3)
                ip = match.group(4) if len(match.groups()) > 3 else "N/A"
                
                # FILTRAR consultas internas do Pi-hole
                if ip == "127.0.0.1#53" or ip == "127.0.0.1" or ip == "localhost":
                    return None
                
                # Determinar status baseado no conteúdo da linha
                status = "allowed"
                if "blocked" in line.lower() or "blacklisted" in line.lower():
                    status = "blocked"
                
                return {
                    "timestamp": timestamp,
                    "type": query_type,
                    "domain": domain,
                    "ip": ip,
                    "status": status,
                    "raw_line": line
                }
            elif "forwarded" in line:
                # Para logs de forwarded
                domain = match.group(2)
                info = match.group(3) if len(match.groups()) > 2 else ""
                
                # FILTRAR consultas internas do Pi-hole
                if info == "127.0.0.1#53" or info == "127.0.0.1" or info == "localhost":
                    return None
                
                return {
                    "timestamp": timestamp,
                    "type": "FORWARD",
                    "domain": domain,
                    "ip": info,
                    "status": "allowed",
                    "raw_line": line
                }
            elif "cached-stale" in line:
                # Para logs de cached-stale (consultas antigas em cache)
                domain = match.group(2)
                info = match.group(3) if len(match.groups()) > 2 else ""
                
                # FILTRAR consultas internas do Pi-hole
                if info == "127.0.0.1#53" or info == "127.0.0.1" or info == "localhost":
                    return None
                
                return {
                    "timestamp": timestamp,
                    "type": "CACHE_STALE",
                    "domain": domain,
                    "ip": info,
                    "status": "allowed",
                    "raw_line": line
                }
    
    return None

def parse_timestamp(timestamp_str):
    """Converte timestamp do log para objeto datetime - versão SUPER melhorada"""
    try:
        # Formato: "Aug 4 08:21:20" (sem zero à esquerda no dia)
        current_year = datetime.now().year
        
        # Primeiro, tentar adicionar zeros à esquerda se necessário
        parts = timestamp_str.split()
        if len(parts) >= 3:
            month, day, time = parts[0], parts[1], parts[2]
            # Adicionar zero à esquerda no dia se necessário
            if len(day) == 1:
                day = f"0{day}"
            timestamp_str = f"{month} {day} {time}"
        
        # Tentar múltiplos anos para encontrar a data correta
        for year_offset in range(5):  # Tentar mais anos (atual até 4 anos atrás)
            year = current_year - year_offset
            try:
                timestamp_with_year = f"{timestamp_str} {year}"
                parsed_date = datetime.strptime(timestamp_with_year, "%b %d %H:%M:%S %Y")
                
                # Se a data não estiver muito no futuro, aceitar
                if parsed_date <= datetime.now() + timedelta(days=1):
                    logger.debug(f"✅ Timestamp parseado: '{timestamp_str}' -> {parsed_date}")
                    return parsed_date
            except ValueError as e:
                logger.debug(f"⚠️ Falha ao parsear '{timestamp_with_year}': {e}")
                continue
        
        # Se não conseguir com nenhum ano, tentar com ano atual
        try:
            timestamp_with_year = f"{timestamp_str} {current_year}"
            parsed_date = datetime.strptime(timestamp_with_year, "%b %d %H:%M:%S %Y")
            logger.debug(f"✅ Timestamp parseado (ano atual): '{timestamp_str}' -> {parsed_date}")
            return parsed_date
        except ValueError as e:
            logger.debug(f"⚠️ Falha ao parsear com ano atual '{timestamp_with_year}': {e}")
        
        logger.warning(f"⚠️ Não foi possível parsear timestamp '{timestamp_str}'")
        return None
        
    except Exception as e:
        logger.warning(f"⚠️ Erro ao parsear timestamp '{timestamp_str}': {e}")
        return None

def filter_logs(logs, query="", type_filter="", status_filter="", start_date=None, end_date=None):
    """Filtra logs baseado nos critérios fornecidos - versão que filtra consultas internas e cache"""
    filtered_logs = []
    
    logger.info(f"🔍 Aplicando filtros: query='{query}', type='{type_filter}', status='{status_filter}'")
    logger.info(f"🔍 Filtros de data: start_date={start_date}, end_date={end_date}")
    
    # Contadores para debug
    total_logs = len(logs)
    internal_filtered = 0
    cache_filtered = 0
    query_filtered = 0
    type_filtered = 0
    status_filtered = 0
    date_filtered = 0
    date_included = 0
    
    for log in logs:
        # FILTRAR consultas internas do Pi-hole
        if log.get("ip") in ["127.0.0.1#53", "127.0.0.1", "localhost", "N/A"]:
            internal_filtered += 1
            continue
        
        # FILTRAR registros de cache
        if log.get("type") in ["CACHE", "CACHE_STALE"]:
            cache_filtered += 1
            continue
        
        # Filtro de busca geral
        if query:
            query_lower = query.lower()
            log_values = [
                str(log.get("domain", "")),
                str(log.get("ip", "")),
                str(log.get("type", "")),
                str(log.get("status", ""))
            ]
            if not any(query_lower in value.lower() for value in log_values):
                query_filtered += 1
                continue
        
        # Filtro por tipo
        if type_filter and log.get("type") != type_filter:
            type_filtered += 1
            continue
        
        # Filtro por status
        if status_filter and log.get("status") != status_filter:
            status_filtered += 1
            continue
        
        # Filtro por data - MELHORADO
        if start_date or end_date:
            log_timestamp = parse_timestamp(log.get("timestamp", ""))
            if log_timestamp:
                # Comparar timestamp completo (com hora)
                if start_date and log_timestamp < start_date:
                    date_filtered += 1
                    logger.debug(f"❌ Log {log_timestamp} < {start_date} (filtrado)")
                    continue
                
                if end_date and log_timestamp > end_date:
                    date_filtered += 1
                    logger.debug(f"❌ Log {log_timestamp} > {end_date} (filtrado)")
                    continue
                
                date_included += 1
                logger.debug(f"✅ Log {log_timestamp} dentro do período {start_date} - {end_date}")
            else:
                # Se não conseguir parsear o timestamp, incluir para não perder logs
                logger.debug(f"⚠️ Incluindo log sem timestamp parseável: {log.get('timestamp')}")
        else:
            # Se não há filtros de data, incluir todos
            logger.debug(f"✅ Sem filtros de data, incluindo log: {log.get('timestamp')}")
        
        filtered_logs.append(log)
    
    logger.info(f"🔍 RESUMO DOS FILTROS:")
    logger.info(f"   - Total de logs: {total_logs}")
    logger.info(f"   - Consultas internas filtradas: {internal_filtered}")
    logger.info(f"   - Cache filtrado: {cache_filtered}")
    logger.info(f"   - Filtro de query: {query_filtered}")
    logger.info(f"   - Filtro de tipo: {type_filtered}")
    logger.info(f"   - Filtro de status: {status_filtered}")
    logger.info(f"   - Filtro de data: {date_filtered}")
    logger.info(f"   - Logs incluídos por data: {date_included}")
    logger.info(f"   - Logs finais: {len(filtered_logs)}")
    
    return filtered_logs

def extract_base_domain(domain):
    """Extrai o domínio base com agrupamento mais inteligente"""
    if not domain or domain == "N/A":
        return domain
    
    # Lista expandida de domínios conhecidos para agrupamento
    known_domains = [
        # Google/Alphabet
        "google.com", "gstatic.com", "gvt1.com", "gvt2.com", "gvt3.com", "googleapis.com",
        "googlevideo.com", "googleusercontent.com", "google-analytics.com",
        
        # Amazon
        "amazon.com", "amazon.com.br", "amazonaws.com", "amazon-adsystem.com",
        
        # Facebook/Meta
        "facebook.com", "fbcdn.net", "instagram.com", "messenger.com",
        
        # Microsoft
        "microsoft.com", "microsoftonline.com", "office.com", "live.com",
        "bing.com", "msn.com", "skype.com",
        
        # Apple
        "apple.com", "icloud.com", "me.com", "mzstatic.com",
        
        # Netflix
        "netflix.com", "nflxvideo.net", "nflximg.net",
        
        # WhatsApp
        "whatsapp.net", "whatsapp.com",
        
        # Cloudflare
        "cloudflare.com", "cloudflare.net",
        
        # Datadog
        "datadoghq.com", "datadog.com",
        
        # Betha (sistema específico)
        "betha.cloud",
        
        # Amurel
        "amurel.org.br",
        
        # CDNs comuns
        "cdn.jsdelivr.net", "cdnjs.cloudflare.com", "unpkg.com",
        "jsdelivr.net", "bootstrapcdn.com",
        
        # Analytics e tracking
        "doubleclick.net", "googlesyndication.com", "googleadservices.com",
        "facebook.net", "fbsbx.com",
        
        # Streaming
        "youtube.com", "ytimg.com", "googlevideo.com",
        "twitch.tv", "ttvnw.net",
        
        # Redes sociais
        "twitter.com", "t.co", "twimg.com",
        "linkedin.com", "licdn.com",
        "reddit.com", "redd.it",
        
        # E-commerce
        "shopify.com", "shopifycdn.com",
        "ebay.com", "ebaystatic.com",
        
        # Outros serviços populares
        "github.com", "githubusercontent.com",
        "stackoverflow.com", "stackexchange.com",
        "wikipedia.org", "wikimedia.org",
        "dropbox.com", "db.tt",
        "slack.com", "slack-msgs.com"
    ]
    
    # Verificar se o domínio termina com algum dos domínios conhecidos
    for known_domain in known_domains:
        if domain.endswith("." + known_domain) or domain == known_domain:
            return known_domain
    
    # Para domínios .com.br, usar domínio de segundo nível
    if domain.endswith(".com.br"):
        parts = domain.split(".")
        if len(parts) >= 3:
            return f"{parts[-3]}.{parts[-2]}.{parts[-1]}"
    
    # Para outros domínios, tentar extrair domínio de segundo nível
    parts = domain.split(".")
    if len(parts) >= 2:
        # Retornar domínio de segundo nível (ex: example.com de sub.example.com)
        return f"{parts[-2]}.{parts[-1]}"
    
    # Se não conseguir, retornar o domínio original
    return domain

def group_logs(logs, group_by, sort_by="timestamp", sort_order="desc"):
    """Agrupa logs por critério especificado - versão SUPER melhorada"""
    if not group_by:
        return logs
    
    grouped = {}
    
    for log in logs:
        # Determinar a chave de agrupamento
        if group_by == "domain":
            # Usar domínio base para agrupamento
            key = extract_base_domain(log.get("domain", "N/A"))
        elif group_by == "ip":
            key = log.get("ip", "N/A")
        elif group_by == "type":
            key = log.get("type", "N/A")
        elif group_by == "status":
            key = log.get("status", "N/A")
        else:
            key = "N/A"
        
        if key not in grouped:
            # Criar entrada agrupada
            grouped[key] = {
                "timestamp": log.get("timestamp"),
                "domain": key,  # Usar o domínio base
                "ip": log.get("ip"),
                "status": log.get("status"),
                "count": 1,
                "types": set([log.get("type")]),  # Manter tipos únicos
                "subdomains": set([log.get("domain")]),  # Manter subdomínios únicos
                "raw_line": log.get("raw_line")
            }
        else:
            # Incrementar contador
            grouped[key]["count"] += 1
            # Adicionar tipo se não existir
            grouped[key]["types"].add(log.get("type"))
            # Adicionar subdomínio se não existir
            grouped[key]["subdomains"].add(log.get("domain"))
            # Manter o timestamp mais recente
            if log.get("timestamp") > grouped[key]["timestamp"]:
                grouped[key]["timestamp"] = log.get("timestamp")
    
    # Converter para lista e processar tipos e subdomínios
    result = []
    for key, data in grouped.items():
        # Converter set de tipos para string
        types_str = ", ".join(sorted(data["types"]))
        
        # Mostrar alguns subdomínios se houver muitos
        subdomains_list = list(data["subdomains"])
        if len(subdomains_list) <= 3:
            subdomains_str = ", ".join(sorted(subdomains_list))
        else:
            subdomains_str = f"{subdomains_list[0]}, {subdomains_list[1]}, ... (+{len(subdomains_list)-2} mais)"
        
        result.append({
            "timestamp": data["timestamp"],
            "domain": data["domain"],
            "ip": data["ip"],
            "status": data["status"],
            "count": data["count"],
            "types": types_str,
            "subdomains": subdomains_str,
            "raw_line": data["raw_line"]
        })
    
    # Ordenar
    reverse = sort_order == "desc"
    
    if sort_by == "count":
        result.sort(key=lambda x: x["count"], reverse=reverse)
    elif sort_by == "domain":
        result.sort(key=lambda x: x["domain"], reverse=reverse)
    elif sort_by == "ip":
        result.sort(key=lambda x: x["ip"], reverse=reverse)
    else:  # timestamp
        result.sort(key=lambda x: x["timestamp"], reverse=reverse)
    
    return result

def fetch_ftl_database(query="", start_date=None, end_date=None, limit=5000):
    """Busca dados do banco SQLite do Pi-hole FTL"""
    try:
        logger.info(f"🔍 Iniciando busca no banco FTL: query='{query}', start_date={start_date}, end_date={end_date}")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            SSH_CONFIG["host"], 
            username=SSH_CONFIG["username"], 
            password=SSH_CONFIG["password"], 
            timeout=SSH_CONFIG["timeout"]
        )

        # Criar arquivo temporário local para receber o banco
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
            temp_db_path = temp_db.name

        logger.info(f"📁 Copiando banco de dados para: {temp_db_path}")
        
        # Tentar copiar o banco de forma segura
        try:
            # Primeiro, tentar fazer uma cópia local no servidor
            remote_copy_cmd = f"cp {SSH_CONFIG['db_path']} /tmp/pihole-ftl-copy.db"
            stdin, stdout, stderr = ssh.exec_command(remote_copy_cmd)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                # Se a cópia local foi bem-sucedida, copiar o arquivo temporário
                sftp = ssh.open_sftp()
                sftp.get("/tmp/pihole-ftl-copy.db", temp_db_path)
                sftp.close()
                
                # Limpar o arquivo temporário no servidor
                ssh.exec_command("rm -f /tmp/pihole-ftl-copy.db")
                logger.info(f"✅ Banco copiado com sucesso (método seguro)")
            else:
                # Fallback: tentar copiar diretamente
                logger.warning("⚠️ Cópia local falhou, tentando cópia direta...")
                sftp = ssh.open_sftp()
                sftp.get(SSH_CONFIG["db_path"], temp_db_path)
                sftp.close()
                logger.info(f"✅ Banco copiado com sucesso (método direto)")
                
        except Exception as copy_error:
            logger.error(f"❌ Erro na cópia do banco: {copy_error}")
            ssh.close()
            raise
        
        ssh.close()

        # Verificar se o arquivo foi copiado corretamente
        if not os.path.exists(temp_db_path) or os.path.getsize(temp_db_path) == 0:
            raise Exception("Arquivo do banco não foi copiado corretamente")

        # Conectar ao banco local
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Processar query para busca combinada
        query_parts = query.strip().split() if query else []
        ip_query = None
        domain_query = None
        
        # Identificar IP e domínio na query
        for part in query_parts:
            if '.' in part and any(c.isdigit() for c in part):
                # Provavelmente é um IP
                ip_query = part
            elif '.' in part and not any(c.isdigit() for c in part):
                # Provavelmente é um domínio
                domain_query = part
            elif ':' in part:
                # Provavelmente é um IP com porta
                ip_query = part.split(':')[0]
        
        # Construir query SQL
        sql = """
        SELECT 
            timestamp,
            type,
            domain,
            client,
            status,
            reply_type
        FROM queries 
        WHERE 1=1
        """
        params = []

        # Adicionar filtros baseados no tipo de busca
        if ip_query and domain_query:
            # Busca combinada: IP E domínio
            sql += " AND client = ? AND domain LIKE ?"
            params.extend([ip_query, f"%{domain_query}%"])
            logger.info(f"🔍 Busca combinada: IP='{ip_query}' E domínio='{domain_query}'")
        elif ip_query:
            # Busca apenas por IP (busca exata para IPs)
            if '.' in ip_query and any(c.isdigit() for c in ip_query):
                # É um IP, usar busca exata
                sql += " AND client = ?"
                params.append(ip_query)
                logger.info(f"🔍 Busca por IP exato: '{ip_query}'")
            else:
                # Não é um IP, usar LIKE
                sql += " AND client LIKE ?"
                params.append(f"%{ip_query}%")
                logger.info(f"🔍 Busca por cliente: '{ip_query}'")
        elif domain_query:
            # Busca apenas por domínio
            sql += " AND domain LIKE ?"
            params.append(f"%{domain_query}%")
            logger.info(f"🔍 Busca por domínio: '{domain_query}'")
        elif query:
            # Busca geral (fallback)
            sql += " AND (domain LIKE ? OR client LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
            logger.info(f"🔍 Busca geral: '{query}'")

        if start_date:
            sql += " AND timestamp >= ?"
            params.append(int(start_date.timestamp()))

        if end_date:
            sql += " AND timestamp <= ?"
            params.append(int(end_date.timestamp()))

        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        logger.info(f"🔍 Executando SQL: {sql}")
        logger.info(f"🔍 Parâmetros: {params}")

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        # Limpar arquivo temporário
        try:
            os.unlink(temp_db_path)
        except:
            pass

        # Converter para formato de log
        logs = []
        for row in rows:
            try:
                timestamp, type_, domain, client, status, reply_type = row
                
                # Converter timestamp para datetime
                try:
                    dt = datetime.fromtimestamp(timestamp)
                    timestamp_str = dt.strftime("%d/%m/%Y %H:%M:%S")
                except:
                    timestamp_str = str(timestamp)
                
                log_entry = {
                    'timestamp': timestamp_str,
                    'type': str(type_) if type_ else '',
                    'domain': str(domain) if domain else '',
                    'ip': str(client) if client else '',
                    'status': str(status) if status else '',
                    'reply_type': str(reply_type) if reply_type else ''
                }
                logs.append(log_entry)
                
            except Exception as row_error:
                logger.warning(f"⚠️ Erro ao processar linha: {row_error}")
                continue

        logger.info(f"✅ {len(logs)} registros processados com sucesso")
        return logs

    except Exception as e:
        logger.error(f"❌ Erro ao buscar no banco FTL: {e}")
        # Limpar arquivo temporário em caso de erro
        try:
            if 'temp_db_path' in locals():
                os.unlink(temp_db_path)
        except:
            pass
        raise

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/logs")
def get_logs():
    query = request.args.get("query", "").lower().strip()  # Adicionar .strip() para remover espaços
    type_filter = request.args.get("type", "")
    status_filter = request.args.get("status", "")
    lines = request.args.get("lines", "1000")
    
    # Parâmetros de data e hora
    start_date_str = request.args.get("start_date", "")
    start_time_str = request.args.get("start_time", "00:00")
    end_date_str = request.args.get("end_date", "")
    end_time_str = request.args.get("end_time", "23:59")
    
    # Parâmetros de agrupamento
    group_by = request.args.get("group_by", "")
    sort_by = request.args.get("sort_by", "timestamp")
    sort_order = request.args.get("sort_order", "desc")
    
    # DEBUG: Logar todos os parâmetros recebidos
    logger.info(f"🔍 PARÂMETROS RECEBIDOS:")
    logger.info(f"   query: '{query}'")
    logger.info(f"   type_filter: '{type_filter}'")
    logger.info(f"   status_filter: '{status_filter}'")
    logger.info(f"   lines: '{lines}'")
    logger.info(f"   start_date_str: '{start_date_str}'")
    logger.info(f"   start_time_str: '{start_time_str}'")
    logger.info(f"   end_date_str: '{end_date_str}'")
    logger.info(f"   end_time_str: '{end_time_str}'")
    logger.info(f"   group_by: '{group_by}'")
    logger.info(f"   sort_by: '{sort_by}'")
    logger.info(f"   sort_order: '{sort_order}'")
    
    try:
        # Processar datas e horas se fornecidas
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_datetime_str = f"{start_date_str} {start_time_str}"
                start_date = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M")
                logger.info(f"✅ Data/hora inicial parseada: {start_date}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao parsear data/hora inicial '{start_date_str} {start_time_str}': {e}")
        
        if end_date_str:
            try:
                end_datetime_str = f"{end_date_str} {end_time_str}"
                end_date = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
                logger.info(f"✅ Data/hora final parseada: {end_date}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao parsear data/hora final '{end_date_str} {end_time_str}': {e}")
        
        # Verificar se há qualquer filtro aplicado
        has_filters = bool(query or type_filter or status_filter or start_date or end_date)
        logger.info(f"🔍 Filtros aplicados: {has_filters}")
        logger.info(f"   - query: {bool(query)}")
        logger.info(f"   - type_filter: {bool(type_filter)}")
        logger.info(f"   - status_filter: {bool(status_filter)}")
        logger.info(f"   - start_date: {bool(start_date)}")
        logger.info(f"   - end_date: {bool(end_date)}")
        
        # Escolher método de busca
        if has_filters:
            # Usar banco SQLite para busca com filtros (mais histórico)
            logs = fetch_ftl_database(query, start_date, end_date, FILTER_CONFIG["max_results"])
            logger.info(f"🔍 Filtros aplicados, buscando no banco FTL")
        else:
            # Quando não há filtros, buscar últimas 100 linhas do log por padrão
            log_lines = fetch_remote_log_tail(lines=100)
            logger.info(f"🔍 Sem filtros, buscando últimas 100 linhas do log")
            
            # Parse dos logs
            logs = []
            for line in log_lines:
                parsed = parse_log_line(line)
                if parsed:
                    logs.append(parsed)
        
        logger.info(f"📊 Linhas carregadas: {len(logs)}")
        
        # DEBUG: Mostrar alguns exemplos de timestamps
        if logs:
            sample_timestamps = [log.get("timestamp", "") for log in logs[:5]]
            logger.info(f"🔍 Exemplos de timestamps: {sample_timestamps}")
            
            # Mostrar alguns exemplos de logs com IP específico se houver query
            if query:
                matching_logs = [log for log in logs if query in str(log.get("ip", "")).lower()]
                if matching_logs:
                    logger.info(f"🔍 Exemplos de logs com IP '{query}': {[log.get('timestamp') for log in matching_logs[:3]]}")
                else:
                    logger.info(f"🔍 Nenhum log encontrado com IP '{query}'")
        
        # Aplicar filtros
        filtered_logs = filter_logs(logs, query, type_filter, status_filter, start_date, end_date)
        logger.info(f"🔍 Logs filtrados: {len(filtered_logs)} entradas")
        
        # Aplicar agrupamento se solicitado
        if group_by:
            final_logs = group_logs(filtered_logs, group_by, sort_by, sort_order)
            logger.info(f"🔍 Logs agrupados por {group_by}: {len(final_logs)} entradas")
        else:
            final_logs = filtered_logs
            # Ordenar por timestamp (mais recentes primeiro)
            final_logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Limitar resultados se necessário
        total_found = len(final_logs)
        if len(final_logs) > FILTER_CONFIG["max_results"]:
            final_logs = final_logs[:FILTER_CONFIG["max_results"]]
            logger.warning(f"⚠️ Resultados limitados a {FILTER_CONFIG['max_results']} entradas de {total_found} encontradas")
        
        logger.info(f"✅ Logs finais: {len(final_logs)} entradas (de {total_found} encontradas)")
        
        # Retornar também informações sobre o total encontrado
        response_data = {
            "logs": final_logs,
            "total_found": total_found,
            "total_returned": len(final_logs),
            "limited": total_found > len(final_logs)
        }
        
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ ERRO AO PROCESSAR LOGS: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/status")
def status():
    """Status do sistema"""
    try:
        # Informações do arquivo de log
        log_info = {}
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                SSH_CONFIG["host"], 
                username=SSH_CONFIG["username"], 
                password=SSH_CONFIG["password"], 
                timeout=SSH_CONFIG["timeout"]
            )
            
            # Informações do arquivo de log
            stdin, stdout, stderr = ssh.exec_command(f"ls -la {SSH_CONFIG['log_path']}")
            log_stat = stdout.read().decode("utf-8").strip()
            
            # Contar linhas do arquivo de log
            stdin, stdout, stderr = ssh.exec_command(f"wc -l {SSH_CONFIG['log_path']}")
            log_lines = stdout.read().decode("utf-8").strip().split()[0]
            
            log_info = {
                "path": SSH_CONFIG["log_path"],
                "stat": log_stat,
                "total_lines": int(log_lines),
                "last_check": datetime.now().isoformat()
            }
            
            ssh.close()
        except Exception as e:
            log_info = {"error": str(e)}
        
        # Informações do banco SQLite
        db_info = {}
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                SSH_CONFIG["host"], 
                username=SSH_CONFIG["username"], 
                password=SSH_CONFIG["password"], 
                timeout=SSH_CONFIG["timeout"]
            )
            
            # Informações do banco SQLite
            stdin, stdout, stderr = ssh.exec_command(f"ls -la {SSH_CONFIG['db_path']}")
            db_stat = stdout.read().decode("utf-8").strip()
            
            # Contar registros no banco
            stdin, stdout, stderr = ssh.exec_command(f"sqlite3 {SSH_CONFIG['db_path']} 'SELECT COUNT(*) FROM queries'")
            db_count = stdout.read().decode("utf-8").strip()
            
            # Data mais antiga e mais recente
            stdin, stdout, stderr = ssh.exec_command(f"sqlite3 {SSH_CONFIG['db_path']} 'SELECT datetime(MIN(timestamp), \"unixepoch\"), datetime(MAX(timestamp), \"unixepoch\") FROM queries'")
            db_dates = stdout.read().decode("utf-8").strip().split('|')
            
            db_info = {
                "path": SSH_CONFIG["db_path"],
                "stat": db_stat,
                "total_records": int(db_count) if db_count.isdigit() else 0,
                "oldest_date": db_dates[0] if len(db_dates) > 0 else "N/A",
                "newest_date": db_dates[1] if len(db_dates) > 1 else "N/A",
                "last_check": datetime.now().isoformat()
            }
            
            ssh.close()
        except Exception as e:
            db_info = {"error": str(e)}
        
        return jsonify({
            "status": "connected",
            "log_file": log_info,
            "database": db_info,
            "config": {
                "host": SSH_CONFIG["host"],
                "log_path": SSH_CONFIG["log_path"],
                "db_path": SSH_CONFIG["db_path"]
            }
        })
            
    except Exception as e:
        logger.error(f"❌ Erro no status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard/stats')
def dashboard_stats():
    """Retorna estatísticas gerais para o dashboard"""
    try:
        # Buscar dados reais do banco
        logs_data = fetch_ftl_database(limit=1000000)  # Buscar muitos registros para estatísticas
        
        if not logs_data:
            return jsonify({
                'success': False,
                'error': 'Não foi possível acessar o banco de dados'
            })
        
        # Calcular estatísticas reais
        total_queries = len(logs_data)
        blocked_queries = len([log for log in logs_data if log.get('status') == 'blocked' or 'blocked' in str(log.get('status', '')).lower()])
        unique_clients = len(set(log.get('ip', '') for log in logs_data if log.get('ip')))
        unique_domains = len(set(log.get('domain', '') for log in logs_data if log.get('domain')))
        
        return jsonify({
            'success': True,
            'stats': {
                'total_queries': total_queries,
                'blocked_queries': blocked_queries,
                'unique_clients': unique_clients,
                'unique_domains': unique_domains
            }
        })
    except Exception as e:
        logger.error(f"❌ Erro ao carregar estatísticas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/dashboard/top-domains')
def dashboard_top_domains():
    """Retorna os domínios mais consultados"""
    try:
        # Buscar dados reais do banco
        logs_data = fetch_ftl_database(limit=100000)  # Buscar muitos registros
        
        if not logs_data:
            return jsonify({
                'success': False,
                'error': 'Não foi possível acessar o banco de dados'
            })
        
        # Agrupar por domínio
        domain_counts = {}
        for log in logs_data:
            domain = log.get('domain', '')
            if domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        # Ordenar por contagem
        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        domains = []
        for domain, count in sorted_domains:
            domains.append({
                'domain': domain,
                'count': count
            })
        
        return jsonify({
            'success': True,
            'domains': domains
        })
    except Exception as e:
        logger.error(f"❌ Erro ao carregar top domínios: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/dashboard/hourly-activity')
def dashboard_hourly_activity():
    """Retorna atividade por hora das últimas 24 horas"""
    try:
        # Buscar dados reais do banco
        logs_data = fetch_ftl_database(limit=100000)
        
        if not logs_data:
            return jsonify({
                'success': False,
                'error': 'Não foi possível acessar o banco de dados'
            })
        
        # Agrupar por hora
        hourly_data = {}
        total_queries = 0
        
        for log in logs_data:
            try:
                # Converter timestamp para hora
                timestamp = log.get('timestamp', '')
                if timestamp:
                    # Assumir formato "dd/mm/yyyy hh:mm:ss"
                    if ' ' in timestamp:
                        time_part = timestamp.split(' ')[1]
                        hour = int(time_part.split(':')[0])
                        hourly_data[hour] = hourly_data.get(hour, 0) + 1
                        total_queries += 1
            except:
                continue
        
        # Preencher horas sem dados
        hourly_activity = []
        for hour in range(24):
            count = hourly_data.get(hour, 0)
            percentage = (count / total_queries * 100) if total_queries > 0 else 0
            
            hourly_activity.append({
                'hour': hour,
                'count': count,
                'percentage': round(percentage, 1)
            })
        
        return jsonify({
            'success': True,
            'hours': hourly_activity
        })
    except Exception as e:
        logger.error(f"❌ Erro ao carregar atividade por hora: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/dashboard/recent-activity')
def dashboard_recent_activity():
    """Retorna atividade recente"""
    try:
        # Buscar dados reais do banco
        logs_data = fetch_ftl_database(limit=10)  # Apenas 10 registros mais recentes
        
        if not logs_data:
            return jsonify({
                'success': False,
                'error': 'Não foi possível acessar o banco de dados'
            })
        
        recent_activity = []
        for log in logs_data:
            recent_activity.append({
                'time': log.get('timestamp', '').split(' ')[1] if ' ' in log.get('timestamp', '') else log.get('timestamp', ''),
                'domain': log.get('domain', ''),
                'ip': log.get('ip', ''),
                'status': 'blocked' if 'blocked' in str(log.get('status', '')).lower() else 'permitted'
            })
        
        return jsonify({
            'success': True,
            'activity': recent_activity
        })
    except Exception as e:
        logger.error(f"❌ Erro ao carregar atividade recente: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == "__main__":
    app.run(
        host=FLASK_CONFIG["host"], 
        port=FLASK_CONFIG["port"], 
        debug=FLASK_CONFIG["debug"]
    )
