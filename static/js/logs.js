// Logs JavaScript
let originalLogs = [];

// Carregar logs
function loadLogs() {
    showLoading();
    
    const params = new URLSearchParams();
    
    // Adicionar filtros
    const ipSearch = document.getElementById('ip-search').value;
    const domainSearch = document.getElementById('domain-search').value;
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const startTime = document.getElementById('start-time').value;
    const endTime = document.getElementById('end-time').value;
    const lines = document.getElementById('lines-filter').value;
    
    if (ipSearch) params.append('ip', ipSearch);
    if (domainSearch) params.append('domain', domainSearch);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);
    if (lines && lines !== '0') params.append('lines', lines);
    
    fetch(`/api/logs?${params.toString()}`)
        .then(res => res.json())
        .then(data => {
            hideLoading();
            
            if (data.success) {
                originalLogs = data.logs;
                displayLogs(data.logs);
                updateLogCount(data.total_found);
            } else {
                showNotification('Erro ao carregar logs: ' + data.error, 'error');
                displayNoLogs();
            }
        })
        .catch(err => {
            hideLoading();
            console.error('Erro ao carregar logs:', err);
            showNotification('Erro ao carregar logs', 'error');
            displayNoLogs();
        });
}

// Exibir logs
function displayLogs(logs) {
    originalLogs = logs;
    
    const tbody = document.getElementById('logs');
    let html = '';
    
    logs.forEach((log, index) => {
        const statusClass = getStatusClass(log.status);
        const statusText = getStatusText(log.status);
        const timestamp = formatTimestamp(log.timestamp);
        
        html += `
            <tr>
                <td style="white-space: nowrap; font-size: 0.9em;">${timestamp}</td>
                <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis;">${log.domain}</td>
                <td style="white-space: nowrap;">
                    <span class="badge bg-info" style="font-size: 0.8em;">
                        <i class="fas fa-clock"></i> ${log.activity_time || 'N/A'}
                    </span>
                </td>
                <td style="white-space: nowrap;">
                    <span class="status-indicator ${statusClass}"></span>
                    <span class="badge ${statusClass === 'status-blocked' ? 'bg-danger' : 'bg-success'}" style="font-size: 0.8em;">
                        ${statusText}
                    </span>
                </td>
                <td style="white-space: nowrap;">
                    <button class="btn btn-sm btn-outline-primary" onclick="showDetails('${log.domain}', '${log.subdomains || ''}')" style="font-size: 0.8em;">
                        <i class="fas fa-eye"></i> Detalhes
                    </button>
                </td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
    document.getElementById('no-logs').style.display = 'none';
}

// Exibir mensagem de nenhum log
function displayNoLogs() {
    document.getElementById('logs').innerHTML = '';
    document.getElementById('no-logs').style.display = 'block';
    updateLogCount(0);
}

// Atualizar contador de logs
function updateLogCount(count) {
    document.getElementById('log-count').textContent = count.toLocaleString();
}

// Mostrar loading
function showLoading() {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('log-count').style.display = 'none';
    document.getElementById('no-logs').style.display = 'none';
}

// Ocultar loading
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('log-count').style.display = 'inline';
}

// Limpar filtros
function clearFilters() {
    document.getElementById('ip-search').value = '';
    document.getElementById('domain-search').value = '';
    document.getElementById('start-date').value = '';
    document.getElementById('end-date').value = '';
    document.getElementById('start-time').value = '00:00';
    document.getElementById('end-time').value = '23:59';
    document.getElementById('lines-filter').value = '5000';
    
    loadLogs();
}

// Exportar PDF
async function exportPDF() {
    if (originalLogs.length === 0) {
        showNotification('Nenhum log para exportar', 'warning');
        return;
    }
    
    try {
        // Criar PDF usando jsPDF
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        
        // Obter configurações de exportação da API
        let pdfTitle = 'Relatório de Logs do Pi-hole';
        let pdfAuthor = 'Pi-hole Log Viewer';
        let pdfSubject = 'Relatório de Logs';
        
        // Tentar pegar das configurações da API
        try {
            const response = await fetch('/api/config');
            const config = await response.json();
            if (config.success && config.settings) {
                pdfTitle = config.settings.pdfTitle || pdfTitle;
                pdfAuthor = config.settings.pdfAuthor || pdfAuthor;
                pdfSubject = config.settings.pdfSubject || pdfSubject;
            }
        } catch (e) {
            console.log('Usando configurações padrão para PDF');
        }
        
        // Definir metadados do PDF
        doc.setProperties({
            title: pdfTitle,
            author: pdfAuthor,
            subject: pdfSubject,
            creator: 'Pi-hole Log Viewer'
        });
        
        // Título
        doc.setFontSize(18);
        doc.text(pdfTitle, 20, 20);
        
        // Informações
        doc.setFontSize(12);
        doc.text(`Data: ${new Date().toLocaleDateString('pt-BR')}`, 20, 35);
        doc.text(`Total de logs: ${originalLogs.length}`, 20, 45);
        
        // Cabeçalho da tabela com espaçamento melhorado
        doc.setFontSize(10);
        doc.setFont(undefined, 'bold');
        doc.text('Horário', 15, 60);
        doc.text('Domínio', 50, 60);
        doc.text('Tempo de Atividade', 130, 60);
        doc.text('Status', 190, 60);
        
        // Linha separadora
        doc.setLineWidth(0.5);
        doc.line(15, 65, 270, 65);
        
        // Dados
        doc.setFont(undefined, 'normal');
        doc.setFontSize(9); // Fonte menor para melhor ajuste
        let y = 75;
        originalLogs.forEach((log, index) => {
            if (y > 280) {
                doc.addPage();
                y = 20;
            }
            
            // Truncar domínio se muito longo (aumentar limite)
            let domain = log.domain;
            if (domain.length > 30) {
                domain = domain.substring(0, 27) + '...';
            }
            
            // Truncar tempo de atividade se muito longo
            let activityTime = log.activity_time || 'N/A';
            if (activityTime.length > 12) {
                activityTime = activityTime.substring(0, 9) + '...';
            }
            
            doc.text(formatTimestamp(log.timestamp), 15, y);
            doc.text(domain, 50, y);
            doc.text(activityTime, 130, y);
            doc.text(getStatusText(log.status), 190, y);
            
            y += 8;
        });
    
        // Salvar PDF
        doc.save('pihole-logs.pdf');
        showNotification('PDF exportado com sucesso!', 'success');
    } catch (error) {
        console.error('Erro ao exportar PDF:', error);
        showNotification('Erro ao exportar PDF. Verifique o console.', 'error');
    }
}

// Formatar timestamp
function formatTimestamp(timestamp) {
    try {
        const date = new Date(timestamp);
        return date.toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (e) {
        return timestamp;
    }
}

// Obter classe de status
function getStatusClass(status) {
    const blockedTypes = ['blocked', 'blacklisted'];
    return blockedTypes.some(blocked => status.toLowerCase().includes(blocked)) 
        ? 'status-blocked' : 'status-allowed';
}

// Obter texto do status
function getStatusText(status) {
    switch(status) {
        case 'forwarded':
            return 'Permitido';
        case 'blocked':
            return 'Bloqueado';
        case 'cached':
            return 'Cache';
        default:
            return status || 'N/A';
    }
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

// Mostrar detalhes de um domínio
function showDetails(domain, subdomains) {
    const modal = new bootstrap.Modal(document.getElementById('detailsModal'));
    const modalContent = document.getElementById('modal-content');
    const modalTitle = document.getElementById('detailsModalLabel');
    
    modalTitle.textContent = `Detalhes: ${domain}`;
    
    // Mostrar loading
    modalContent.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p>Carregando detalhes...</p></div>';
    modal.show();
    
    // Filtrar os logs originais pelo domínio
    const domainLogs = originalLogs.filter(log => {
        return log.domain && log.domain.includes(domain);
    });
    
    if (domainLogs.length === 0) {
        modalContent.innerHTML = '<div class="alert alert-warning">Nenhum log encontrado para este domínio</div>';
        return;
    }
    
    // Criar tabela de detalhes
    let tableHtml = `
        <h6>Domínio: <code>${domain}</code></h6>
        <p class="text-muted">${domainLogs.length} registros encontrados</p>
        <div class="table-responsive">
            <table class="table table-sm table-striped">
                <thead>
                    <tr>
                        <th>Horário</th>
                        <th>Domínio</th>
                        <th>Tempo de Atividade</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    domainLogs.forEach(log => {
        const statusClass = getStatusClass(log.status);
        const statusText = getStatusText(log.status);
        
        tableHtml += `
            <tr>
                <td>${formatTimestamp(log.timestamp)}</td>
                <td><code>${log.domain}</code></td>
                <td>
                    <span class="badge bg-info">
                        <i class="fas fa-clock"></i> ${log.activity_time || 'N/A'}
                    </span>
                </td>
                <td>
                    <span class="status-indicator ${statusClass}"></span>
                    <span class="badge ${statusClass === 'status-blocked' ? 'bg-danger' : 'bg-success'}">
                        ${statusText}
                    </span>
                </td>
            </tr>
        `;
    });
    
    tableHtml += `
                </tbody>
            </table>
        </div>
    `;
    
    modalContent.innerHTML = tableHtml;
}

// Carregar logs ao iniciar
document.addEventListener('DOMContentLoaded', function() {
    loadLogs();
}); 