# ⚡ Configuração Rápida

## 🚀 Passos para começar em 5 minutos

### 1. Clone e configure
```bash
git clone https://github.com/seu-usuario/pihole-log-viewer.git
cd pihole-log-viewer
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configure as credenciais
```bash
cp config.example.py config.py
# Edite config.py com suas informações SSH
```

### 3. Execute
```bash
python app_local_db.py
```

### 4. Acesse
```
http://localhost:8082
```

## 🔧 Configuração do Telegram (Opcional)

1. **Crie um bot:** Procure `@BotFather` no Telegram
2. **Obtenha o Chat ID:** Adicione o bot a um grupo e acesse:
   ```
   https://api.telegram.org/botSEU_TOKEN/getUpdates
   ```
3. **Configure:** Acesse `http://localhost:8082/config`

## 📁 Arquivos importantes

- `config.py` - **NÃO VERSIONADO** (contém senhas)
- `alert_settings.json` - **NÃO VERSIONADO** (contém tokens)
- `*.db` - **NÃO VERSIONADO** (banco de dados local)

## 🆘 Problemas comuns

### Erro de conexão SSH
- Verifique IP, usuário e senha no `config.py`
- Teste: `ssh usuario@ip-do-servidor`

### Bot não funciona
- Verifique se o bot foi adicionado ao grupo
- Confirme Chat ID (grupos começam com `-`)

### Dados não aparecem
- Verifique se o Pi-hole está rodando
- Confirme caminhos no `config.py`

---

**Para mais detalhes, veja o [README.md](README.md) completo!** 