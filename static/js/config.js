// Config JavaScript

// Salvar configurações
function saveConfig() {
    const config = {
        maxResults: document.getElementById('max-results').value,
        cacheTimeout: document.getElementById('cache-timeout').value,
        autoRefresh: document.getElementById('auto-refresh').value,
        updateInterval: document.getElementById('update-interval').value,
        dataRetention: document.getElementById('data-retention').value,
        dashboardUpdate: document.getElementById('dashboard-update').value,
        pdfTitle: document.getElementById('pdf-title').value,
        pdfAuthor: document.getElementById('pdf-author').value,
        pdfSubject: document.getElementById('pdf-subject').value,
        // Configurações de alertas
        alertsEnabled: document.getElementById('alerts-enabled').value,
        ipSpikeThreshold: document.getElementById('ip-spike-threshold').value,
        domainSpikeThreshold: document.getElementById('domain-spike-threshold').value,
        networkSpikeThreshold: document.getElementById('network-spike-threshold').value,
        analysisPeriodHours: document.getElementById('analysis-period-hours').value,
        telegramEnabled: document.getElementById('telegram-enabled').value,
        telegramChatId: document.getElementById('telegram-chat-id').value,
        telegramBotToken: document.getElementById('telegram-bot-token').value
    };
    
    fetch('/api/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showNotification('Configurações salvas com sucesso!', 'success');
        } else {
            showNotification('Erro ao salvar configurações: ' + data.error, 'error');
        }
    })
    .catch(err => {
        console.error('Erro ao salvar configurações:', err);
        showNotification('Erro ao salvar configurações', 'error');
    });
}

// Resetar configurações
function resetConfig() {
    if (confirm('Tem certeza que deseja restaurar as configurações padrão?')) {
        // Restaurar valores padrão
        document.getElementById('max-results').value = '5000';
        document.getElementById('cache-timeout').value = '300';
        document.getElementById('auto-refresh').value = '0';
        document.getElementById('update-interval').value = '30';
        document.getElementById('data-retention').value = '90';
        document.getElementById('dashboard-update').value = '30';
        document.getElementById('pdf-title').value = 'Relatório de Logs do Pi-hole';
        document.getElementById('pdf-author').value = 'Pi-hole Log Viewer';
        document.getElementById('pdf-subject').value = 'Relatório de DNS';
        // Configurações de alertas padrão
        document.getElementById('alerts-enabled').value = 'true';
        document.getElementById('ip-spike-threshold').value = '3.0';
        document.getElementById('domain-spike-threshold').value = '5.0';
        document.getElementById('network-spike-threshold').value = '2.5';
        document.getElementById('analysis-period-hours').value = '2';
        document.getElementById('telegram-enabled').value = 'false';
        document.getElementById('telegram-chat-id').value = '';
        document.getElementById('telegram-bot-token').value = '';
        
        showNotification('Configurações restauradas para os padrões!', 'info');
    }
}

// Exportar configurações
function exportConfig() {
    const config = {
        maxResults: document.getElementById('max-results').value,
        cacheTimeout: document.getElementById('cache-timeout').value,
        autoRefresh: document.getElementById('auto-refresh').value,
        updateInterval: document.getElementById('update-interval').value,
        dataRetention: document.getElementById('data-retention').value,
        dashboardUpdate: document.getElementById('dashboard-update').value,
        pdfTitle: document.getElementById('pdf-title').value,
        pdfAuthor: document.getElementById('pdf-author').value,
        pdfSubject: document.getElementById('pdf-subject').value,
        // Configurações de alertas
        alertsEnabled: document.getElementById('alerts-enabled').value,
        ipSpikeThreshold: document.getElementById('ip-spike-threshold').value,
        domainSpikeThreshold: document.getElementById('domain-spike-threshold').value,
        networkSpikeThreshold: document.getElementById('network-spike-threshold').value,
        analysisPeriodHours: document.getElementById('analysis-period-hours').value,
        telegramEnabled: document.getElementById('telegram-enabled').value,
        telegramChatId: document.getElementById('telegram-chat-id').value,
        telegramBotToken: document.getElementById('telegram-bot-token').value
    };
    
    const dataStr = JSON.stringify(config, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = 'pihole-config.json';
    link.click();
    
    showNotification('Configuração exportada com sucesso!', 'success');
}

// Importar configurações
function importConfig() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = function(e) {
        const file = e.target.files[0];
        const reader = new FileReader();
        
        reader.onload = function(e) {
            try {
                const config = JSON.parse(e.target.result);
                
                // Aplicar configurações
                if (config.maxResults) document.getElementById('max-results').value = config.maxResults;
                if (config.cacheTimeout) document.getElementById('cache-timeout').value = config.cacheTimeout;
                if (config.autoRefresh) document.getElementById('auto-refresh').value = config.autoRefresh;
                if (config.updateInterval) document.getElementById('update-interval').value = config.updateInterval;
                if (config.dataRetention) document.getElementById('data-retention').value = config.dataRetention;
                if (config.dashboardUpdate) document.getElementById('dashboard-update').value = config.dashboardUpdate;
                if (config.pdfTitle) document.getElementById('pdf-title').value = config.pdfTitle;
                if (config.pdfAuthor) document.getElementById('pdf-author').value = config.pdfAuthor;
                if (config.pdfSubject) document.getElementById('pdf-subject').value = config.pdfSubject;
                // Configurações de alertas
                if (config.alertsEnabled) document.getElementById('alerts-enabled').value = config.alertsEnabled;
                if (config.ipSpikeThreshold) document.getElementById('ip-spike-threshold').value = config.ipSpikeThreshold;
                if (config.domainSpikeThreshold) document.getElementById('domain-spike-threshold').value = config.domainSpikeThreshold;
                if (config.networkSpikeThreshold) document.getElementById('network-spike-threshold').value = config.networkSpikeThreshold;
                if (config.analysisPeriodHours) document.getElementById('analysis-period-hours').value = config.analysisPeriodHours;
                if (config.telegramEnabled) document.getElementById('telegram-enabled').value = config.telegramEnabled;
                if (config.telegramChatId) document.getElementById('telegram-chat-id').value = config.telegramChatId;
                if (config.telegramBotToken) document.getElementById('telegram-bot-token').value = config.telegramBotToken;
                
                showNotification('Configuração importada com sucesso!', 'success');
            } catch (error) {
                showNotification('Erro ao importar configuração: ' + error.message, 'error');
            }
        };
        
        reader.readAsText(file);
    };
    
    input.click();
}

// Carregar configurações
function loadConfig() {
    fetch('/api/config')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const config = data.settings;
                
                // Aplicar configurações
                if (config.maxResults) document.getElementById('max-results').value = config.maxResults;
                if (config.cacheTimeout) document.getElementById('cache-timeout').value = config.cacheTimeout;
                if (config.autoRefresh) document.getElementById('auto-refresh').value = config.autoRefresh;
                if (config.updateInterval) document.getElementById('update-interval').value = config.updateInterval;
                if (config.dataRetention) document.getElementById('data-retention').value = config.dataRetention;
                if (config.dashboardUpdate) document.getElementById('dashboard-update').value = config.dashboardUpdate;
                if (config.pdfTitle) document.getElementById('pdf-title').value = config.pdfTitle;
                if (config.pdfAuthor) document.getElementById('pdf-author').value = config.pdfAuthor;
                if (config.pdfSubject) document.getElementById('pdf-subject').value = config.pdfSubject;
                // Configurações de alertas
                if (config.alertsEnabled) document.getElementById('alerts-enabled').value = config.alertsEnabled;
                if (config.ipSpikeThreshold) document.getElementById('ip-spike-threshold').value = config.ipSpikeThreshold;
                if (config.domainSpikeThreshold) document.getElementById('domain-spike-threshold').value = config.domainSpikeThreshold;
                if (config.networkSpikeThreshold) document.getElementById('network-spike-threshold').value = config.networkSpikeThreshold;
                if (config.analysisPeriodHours) document.getElementById('analysis-period-hours').value = config.analysisPeriodHours;
                if (config.telegramEnabled) document.getElementById('telegram-enabled').value = config.telegramEnabled;
                if (config.telegramChatId) document.getElementById('telegram-chat-id').value = config.telegramChatId;
                if (config.telegramBotToken) document.getElementById('telegram-bot-token').value = config.telegramBotToken;
            }
        })
        .catch(err => {
            console.error('Erro ao carregar configurações:', err);
        });
}

// Testar notificação
function testNotification() {
    const telegramEnabled = document.getElementById('telegram-enabled').value;
    
    if (telegramEnabled === 'false') {
        showNotification('Habilite as notificações Telegram primeiro!', 'warning');
        return;
    }
    
    const chatId = document.getElementById('telegram-chat-id').value;
    const botToken = document.getElementById('telegram-bot-token').value;
    
    if (!chatId || !botToken) {
        showNotification('Configure Chat ID e Bot Token do Telegram!', 'warning');
        return;
    }
    
    // Mostrar loading
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testando...';
    button.disabled = true;
    
    fetch('/api/test-notification')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('✅ Notificação de teste enviada com sucesso!', 'success');
            } else {
                showNotification('❌ Erro ao enviar notificação: ' + data.error, 'error');
            }
        })
        .catch(error => {
            showNotification('❌ Erro ao testar notificação: ' + error.message, 'error');
        })
        .finally(() => {
            button.innerHTML = originalText;
            button.disabled = false;
        });
}

// Mostrar notificação
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Carregar configurações ao iniciar
document.addEventListener('DOMContentLoaded', function() {
    loadConfig();
}); 