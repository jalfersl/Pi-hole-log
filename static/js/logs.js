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
    const tbody = document.getElementById('logs');
    
    console.log('Logs recebidos:', logs);
    
    if (!logs || logs.length === 0) {
        displayNoLogs();
        return;
    }
    
    let html = '';
    logs.forEach(log => {
        const statusClass = getStatusClass(log.status);
        const statusText = getStatusText(log.status);
        
        console.log('Processando log:', log);
        
        html += `
            <tr>
                <td><small>${formatTimestamp(log.timestamp)}</small></td>
                <td><code>${log.domain}</code></td>
                <td><code>${log.ip}</code></td>
                <td>
                    <span class="status-indicator ${statusClass}"></span>
                    ${statusText}
                    <span class="badge bg-secondary ms-2">${log.count}</span>
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
                pdfTitle = config.settings.pdf_title || pdfTitle;
                pdfAuthor = config.settings.pdf_author || pdfAuthor;
                pdfSubject = config.settings.pdf_subject || pdfSubject;
            }
        } catch (e) {
            console.log('Usando configurações padrão para PDF');
        }
        
        // Sobrescrever com valores dos campos se existirem
        const titleField = document.getElementById('pdf-title');
        const authorField = document.getElementById('pdf-author');
        const subjectField = document.getElementById('pdf-subject');
        
        if (titleField && titleField.value) {
            pdfTitle = titleField.value;
            console.log('Título do PDF:', pdfTitle);
        }
        if (authorField && authorField.value) {
            pdfAuthor = authorField.value;
            console.log('Autor do PDF:', pdfAuthor);
        }
        if (subjectField && subjectField.value) {
            pdfSubject = subjectField.value;
            console.log('Assunto do PDF:', pdfSubject);
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
        doc.text('Horário', 20, 60);
        doc.text('Domínio', 80, 60);
        doc.text('IP', 160, 60);
        doc.text('Status', 190, 60);
        
        // Linha separadora
        doc.setLineWidth(0.5);
        doc.line(20, 65, 190, 65);
        
        // Dados
        doc.setFont(undefined, 'normal');
        let y = 75;
        originalLogs.forEach((log, index) => {
            if (y > 280) {
                doc.addPage();
                y = 20;
            }
            
            doc.text(formatTimestamp(log.timestamp), 20, y);
            doc.text(log.domain, 80, y);
            doc.text(log.ip, 160, y);
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

// Obter texto de status
function getStatusText(status) {
    const blockedTypes = ['blocked', 'blacklisted'];
    return blockedTypes.some(blocked => status.toLowerCase().includes(blocked)) 
        ? 'Bloqueado' : 'Permitido';
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

// Carregar logs ao iniciar
document.addEventListener('DOMContentLoaded', function() {
    loadLogs();
}); 