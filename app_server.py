#!/usr/bin/env python3
"""
Pi-hole Log Viewer - Versão Otimizada para Servidor
Acesso direto ao banco SQLite sem SFTP
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import os
from config import FLASK_CONFIG, LOGGING_CONFIG, FILTER_CONFIG

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
    datefmt=LOGGING_CONFIG["date_format"]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuração do banco
DB_PATH = "/etc/pihole/pihole-FTL.db"

def check_database_access():
    """Verifica se conseguimos acessar o banco de dados"""
    try:
        if not os.path.exists(DB_PATH):
            logger.error(f"❌ Banco de dados não encontrado: {DB_PATH}")
            return False
        
        # Testar conexão
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM queries LIMIT 1")
        count = cursor.fetchone()[0]
        conn.close()
        
        logger.info(f"✅ Banco de dados acessível: {count} registros")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao acessar banco: {e}")
        return False

def fetch_ftl_data(query="", start_date=None, end_date=None, limit=5000):
    """Busca dados diretamente do banco SQLite"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

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

        # Adicionar filtros
        if query:
            sql += " AND (domain LIKE ? OR client LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])

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

        # Executar query
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        logger.info(f"📊 Resultados encontrados: {len(rows)}")

        # Converter para formato compatível
        logs = []
        for row in rows:
            timestamp, query_type, domain, client, status, reply_type = row
            
            # Converter timestamp para datetime
            try:
                dt = datetime.fromtimestamp(timestamp)
                timestamp_str = dt.strftime("%b %d %H:%M:%S")
            except (ValueError, TypeError):
                timestamp_str = "Jan 01 00:00:00"
                dt = datetime.now()
            
            # Garantir que todos os campos são strings
            logs.append({
                "timestamp": timestamp_str,
                "type": str(query_type) if query_type is not None else "",
                "domain": str(domain) if domain is not None else "",
                "ip": str(client) if client is not None else "",
                "status": "blocked" if status == 1 else "allowed",
                "raw_line": f"{timestamp_str} query[{query_type}] {domain} from {client}",
                "reply": str(reply_type) if reply_type is not None else ""
            })

        conn.close()
        logger.info(f"✅ Dados carregados: {len(logs)} entradas")
        return logs

    except Exception as e:
        logger.error(f"❌ Erro ao buscar dados: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise

@app.route("/")
def index():
    """Página principal"""
    return render_template("index.html")

@app.route("/status")
def status():
    """Status do sistema"""
    try:
        # Verificar acesso ao banco
        db_accessible = check_database_access()
        
        # Informações do banco
        if db_accessible:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Total de registros
            cursor.execute("SELECT COUNT(*) FROM queries")
            total_records = cursor.fetchone()[0]
            
            # Data mais antiga e mais recente
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM queries")
            min_ts, max_ts = cursor.fetchone()
            
            oldest_date = datetime.fromtimestamp(min_ts).strftime("%Y-%m-%d %H:%M:%S") if min_ts else "N/A"
            newest_date = datetime.fromtimestamp(max_ts).strftime("%Y-%m-%d %H:%M:%S") if max_ts else "N/A"
            
            conn.close()
            
            return jsonify({
                "status": "connected",
                "database": {
                    "path": DB_PATH,
                    "total_records": total_records,
                    "oldest_date": oldest_date,
                    "newest_date": newest_date
                },
                "last_check": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "error": "Database not accessible",
                "last_check": datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"❌ Erro no status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/logs")
def get_logs():
    """API para buscar logs"""
    query = request.args.get("query", "").lower().strip()
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
        
        # Buscar dados do banco
        logs = fetch_ftl_data(query, start_date, end_date, FILTER_CONFIG["max_results"])
        
        # Aplicar filtros adicionais
        filtered_logs = []
        for log in logs:
            # Filtro por tipo
            if type_filter and log.get("type") != type_filter:
                continue
            
            # Filtro por status
            if status_filter and log.get("status") != status_filter:
                continue
            
            filtered_logs.append(log)
        
        # Ordenar por timestamp
        if sort_order == "desc":
            filtered_logs.sort(key=lambda x: x["timestamp"], reverse=True)
        else:
            filtered_logs.sort(key=lambda x: x["timestamp"])
        
        # Limitar resultados se necessário
        total_found = len(filtered_logs)
        if len(filtered_logs) > FILTER_CONFIG["max_results"]:
            filtered_logs = filtered_logs[:FILTER_CONFIG["max_results"]]
            logger.warning(f"⚠️ Resultados limitados a {FILTER_CONFIG['max_results']} entradas de {total_found} encontradas")
        
        logger.info(f"✅ Logs finais: {len(filtered_logs)} entradas (de {total_found} encontradas)")
        
        # Retornar resposta
        response_data = {
            "logs": filtered_logs,
            "total_found": total_found,
            "total_returned": len(filtered_logs),
            "limited": total_found > len(filtered_logs)
        }
        
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ ERRO AO PROCESSAR LOGS: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Verificar acesso ao banco na inicialização
    if check_database_access():
        logger.info("🚀 Iniciando Pi-hole Log Viewer (Versão Servidor)")
        app.run(
            host=FLASK_CONFIG["host"],
            port=FLASK_CONFIG["port"],
            debug=FLASK_CONFIG["debug"]
        )
    else:
        logger.error("❌ Não foi possível acessar o banco de dados. Verifique as permissões.")
        exit(1) 