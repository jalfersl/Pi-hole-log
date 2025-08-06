# Configurações da aplicação Pi-hole Log Viewer

# Configurações SSH
SSH_CONFIG = {
    "host": "SEU_IP_DO_SERVIDOR",
    "username": "SEU_USUARIO", 
    "password": "SUA_SENHA",
    "timeout": 10,
    "log_path": "/var/log/pihole/pihole.log",
    "db_path": "/etc/pihole/pihole-FTL.db"
}

# Configurações da aplicação Flask
FLASK_CONFIG = {
    "host": "0.0.0.0",
    "port": 8082,
    "debug": True
}

# Configurações de logging
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}

# Configurações de filtros
FILTER_CONFIG = {
    "max_results": 5000,
    "default_sort": "timestamp_desc"
}

# Tipos de query DNS suportados
DNS_QUERY_TYPES = [
    "A", "AAAA", "CNAME", "MX", "TXT", "NS", "PTR", "SOA", "SRV", "CAA"
]

# Configurações do Banco Local
LOCAL_DB_CONFIG = {
    "path": "pihole_logs.db",
    "enabled": True
} 