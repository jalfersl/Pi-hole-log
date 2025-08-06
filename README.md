# 🔍 Pi-hole Log Viewer

Um sistema completo para visualização e análise de logs do Pi-hole com interface web moderna, alertas em tempo real via Telegram e exportação de relatórios em PDF.

## ✨ Funcionalidades

### 📊 Dashboard
- **Estatísticas em tempo real** - Consultas bloqueadas/permitidas
- **Gráfico de atividade por hora** - Visualização da atividade do dia atual
- **Top IPs e Domínios** - Lista dos endereços mais ativos
- **Atualização automática** - Dados sincronizados com Pi-hole FTL

### 📋 Logs
- **Busca avançada** - Filtros por IP, domínio, data/hora
- **Agrupamento inteligente** - Registros similares agrupados
- **Exportação PDF** - Relatórios personalizáveis
- **Paginação** - Navegação por grandes volumes de dados

### ⚙️ Configurações
- **Alertas inteligentes** - Detecção de picos de tráfego
- **Notificações Telegram** - Alertas em tempo real
- **Retenção de dados** - Configuração de período de armazenamento
- **Atualização automática** - Sincronização configurável

## 🚀 Instalação

### Pré-requisitos
- Python 3.8+
- Pi-hole instalado e funcionando
- Acesso SSH ao servidor Pi-hole

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/pihole-log-viewer.git
cd pihole-log-viewer
```

### 2. Configure o ambiente virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure o arquivo de configuração
```bash
cp config.example.py config.py
```

Edite o arquivo `config.py` com suas informações:
```python
SSH_CONFIG = {
    "host": "SEU_IP_DO_SERVIDOR",
    "username": "SEU_USUARIO", 
    "password": "SUA_SENHA",
    "timeout": 10,
    "log_path": "/var/log/pihole/pihole.log",
    "db_path": "/etc/pihole/pihole-FTL.db"
}
```

### 5. Configure as configurações de alerta
```bash
cp alert_settings.example.json alert_settings.json
```

Edite o arquivo `alert_settings.json` com suas configurações de Telegram (opcional).

## 🔧 Configuração do Telegram (Opcional)

### 1. Crie um bot no Telegram
1. Abra o Telegram e procure por `@BotFather`
2. Envie `/newbot`
3. Siga as instruções para criar seu bot
4. Guarde o **Bot Token** fornecido

### 2. Obtenha o Chat ID
1. Adicione seu bot a um grupo ou converse diretamente
2. Acesse: `https://api.telegram.org/botSEU_BOT_TOKEN/getUpdates`
3. Procure pelo `chat_id` na resposta JSON
4. Para grupos, o ID começa com `-` (ex: `-1234567890`)

### 3. Configure no sistema
1. Acesse: `http://seu-ip:8082/config`
2. Preencha o **Chat ID** e **Bot Token**
3. Habilite as notificações
4. Teste o bot

## 🏃‍♂️ Execução

### Iniciar a aplicação
```bash
python app_local_db.py
```

A aplicação estará disponível em: `http://localhost:8082`

### Iniciar atualização automática (opcional)
```bash
python auto_update.py
```

## 📱 Interface Web

### Dashboard (`/`)
- Visão geral das estatísticas
- Gráficos de atividade
- Top IPs e domínios
- Botão de atualização manual

### Logs (`/logs`)
- Busca e filtros avançados
- Agrupamento de registros
- Exportação em PDF
- Configurações de cabeçalho

### Configurações (`/config`)
- Configurações de alertas
- Configuração do Telegram
- Configurações de exportação PDF
- Teste de notificações

## ⚙️ Configurações Avançadas

### Alertas
- **Threshold IP**: Multiplicador para detectar picos por IP (padrão: 3.0)
- **Threshold Domínio**: Multiplicador para detectar picos por domínio (padrão: 5.0)
- **Threshold Rede**: Multiplicador para detectar picos na rede (padrão: 2.5)
- **Período de Análise**: Horas para calcular a média (padrão: 2)

### Exportação PDF
- **Título**: Título do relatório
- **Autor**: Autor do documento
- **Assunto**: Assunto do relatório

### Retenção de Dados
- **Período**: Dias para manter os dados (padrão: 90)

## 🔒 Segurança

### Recomendações
1. **Use chaves SSH** em vez de senhas
2. **Configure firewall** para limitar acesso
3. **Use HTTPS** em produção
4. **Mantenha o sistema atualizado**

### Arquivos sensíveis
- `config.py` - Contém senhas SSH
- `alert_settings.json` - Contém tokens do Telegram
- `*.db` - Bancos de dados locais

## 🐛 Solução de Problemas

### Erro de conexão SSH
- Verifique se o servidor está acessível
- Confirme usuário e senha
- Teste a conexão manualmente

### Bot do Telegram não funciona
- Verifique se o bot foi adicionado ao grupo
- Confirme se o Chat ID está correto
- Teste o bot diretamente via API

### Dados não aparecem
- Verifique se o Pi-hole está funcionando
- Confirme os caminhos dos arquivos
- Teste a conexão SSH

## 📊 Estrutura do Projeto

```
pihole-log-viewer/
├── app_local_db.py          # Aplicação principal
├── auto_update.py           # Atualização automática
├── config.py               # Configurações (não versionado)
├── config.example.py       # Exemplo de configuração
├── requirements.txt        # Dependências Python
├── static/                # Arquivos estáticos
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── dashboard.js
│       ├── logs.js
│       └── config.js
├── templates/             # Templates HTML
│   ├── base.html
│   ├── dashboard.html
│   ├── logs.html
│   └── config.html
└── README.md             # Este arquivo
```

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🙏 Agradecimentos

- [Pi-hole](https://pi-hole.net/) - Sistema de bloqueio de anúncios
- [Flask](https://flask.palletsprojects.com/) - Framework web
- [Chart.js](https://www.chartjs.org/) - Gráficos interativos
- [Bootstrap](https://getbootstrap.com/) - Framework CSS

## 📞 Suporte

Se você encontrar algum problema ou tiver dúvidas:

1. **Abra uma issue** no GitHub
2. **Verifique a documentação** acima
3. **Consulte os logs** da aplicação

---

**Desenvolvido por Jardel Fuchter com ❤️ para monitoramento de redes Pi-hole** 