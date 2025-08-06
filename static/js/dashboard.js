// Dashboard JavaScript
let activityChart = null;

// Atualizar dados do Pi-hole e recarregar dashboard
function updateAndReloadData() {
    // Mostrar loading no botão
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Atualizando...';
    button.disabled = true;
    
    // Primeiro atualizar dados do Pi-hole
    fetch('/api/update-data')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                console.log('✅ Dados atualizados:', data.message);
                // Agora recarregar dashboard
                loadDashboardData();
                showNotification('Dados atualizados com sucesso!', 'success');
            } else {
                console.error('❌ Erro na atualização:', data.error);
                showNotification('Erro ao atualizar dados', 'error');
            }
        })
        .catch(err => {
            console.error('❌ Erro na atualização:', err);
            showNotification('Erro ao atualizar dados', 'error');
        })
        .finally(() => {
            // Restaurar botão
            button.innerHTML = originalText;
            button.disabled = false;
        });
}

// Carregar dados do dashboard
function loadDashboardData() {
    // Carregar estatísticas
    loadStats();
    
    // Carregar gráfico de atividade
    loadActivityChart();
    
    // Carregar top lists
    loadTopDomains();
    loadTopBlockedDomains();
    loadTopIPs();
    
    // Carregar atividade recente
    loadRecentActivity();
    
    // Carregar alertas
    loadAlerts();
    
    // Atualizar última atualização
    updateLastUpdate();
}

// Carregar estatísticas
function loadStats() {
    fetch('/api/stats')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('total-queries').textContent = data.stats.total_queries.toLocaleString();
                document.getElementById('blocked-queries').textContent = data.stats.blocked_queries.toLocaleString();
                document.getElementById('unique-clients').textContent = data.stats.unique_clients.toLocaleString();
                document.getElementById('block-rate').textContent = data.stats.block_rate + '%';
            }
        })
        .catch(err => {
            console.error('Erro ao carregar estatísticas:', err);
        });
}

// Carregar gráfico de atividade
function loadActivityChart() {
    fetch('/api/activity-chart')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                createActivityChart(data.data);
            }
        })
        .catch(err => {
            console.error('Erro ao carregar gráfico:', err);
        });
}

// Criar gráfico de atividade
function createActivityChart(data) {
    const ctx = document.getElementById('activityChart').getContext('2d');
    
    if (activityChart) {
        activityChart.destroy();
    }
    
    activityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Consultas',
                    data: data.queries,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    borderWidth: 2
                },
                {
                    label: 'Bloqueadas',
                    data: data.blocked,
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    tension: 0.4,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 11
                        },
                        usePointStyle: true,
                        padding: 15
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        font: {
                            size: 9
                        }
                    },
                    grid: {
                        color: 'rgba(0,0,0,0.1)',
                        drawBorder: false
                    }
                },
                x: {
                    ticks: {
                        font: {
                            size: 9
                        }
                    },
                    grid: {
                        color: 'rgba(0,0,0,0.1)',
                        drawBorder: false
                    }
                }
            },
            elements: {
                point: {
                    radius: 3,
                    hoverRadius: 5
                }
            }
        }
    });
}

// Carregar top domínios
function loadTopDomains() {
    fetch('/api/top-domains')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                displayTopList('top-domains', data.domains, 'domain', 'count');
            }
        })
        .catch(err => {
            console.error('Erro ao carregar top domínios:', err);
        });
}

// Carregar top domínios bloqueados
function loadTopBlockedDomains() {
    fetch('/api/top-blocked-domains')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                displayTopList('top-blocked-domains', data.domains, 'domain', 'count');
            }
        })
        .catch(err => {
            console.error('Erro ao carregar top domínios bloqueados:', err);
        });
}

// Carregar top IPs
function loadTopIPs() {
    fetch('/api/top-ips')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                displayTopList('top-ips', data.ips, 'ip', 'count');
            }
        })
        .catch(err => {
            console.error('Erro ao carregar top IPs:', err);
        });
}

// Exibir lista top (sem porcentagem)
function displayTopList(containerId, items, labelField, countField) {
    const container = document.getElementById(containerId);
    
    if (!items || items.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">Nenhum dado disponível</div>';
        return;
    }
    
    let html = '<div class="list-group list-group-flush">';
    items.forEach((item, index) => {
        const label = item[labelField];
        const count = item[countField];
        
        html += `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <span class="badge bg-primary me-2">${index + 1}</span>
                    <code>${label}</code>
                </div>
                <div class="text-end">
                    <span class="badge bg-success">${count.toLocaleString()}</span>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

// Carregar atividade recente
function loadRecentActivity() {
    fetch('/api/recent-activity')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                displayRecentActivity(data.activities);
            }
        })
        .catch(err => {
            console.error('Erro ao carregar atividade recente:', err);
        });
}

// Exibir atividade recente
function displayRecentActivity(activities) {
    const container = document.getElementById('recent-activity');
    
    if (!activities || activities.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">Nenhuma atividade recente</div>';
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table table-sm">';
    html += '<thead><tr><th>Horário</th><th>Domínio</th><th>IP</th><th>Status</th></tr></thead><tbody>';
    
    activities.forEach(activity => {
        const statusClass = activity.status === 'blocked' ? 'status-blocked' : 'status-allowed';
        const statusText = activity.status === 'blocked' ? 'Bloqueado' : 'Permitido';
        
        html += `
            <tr>
                <td><small>${formatTimestamp(activity.timestamp)}</small></td>
                <td><code>${activity.domain}</code></td>
                <td><code>${activity.ip}</code></td>
                <td>
                    <span class="status-indicator ${statusClass}"></span>
                    ${statusText}
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Carregar alertas
function loadAlerts() {
    fetch('/api/alerts')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                displayAlerts(data.alerts);
            }
        })
        .catch(err => {
            console.error('Erro ao carregar alertas:', err);
        });
}

// Exibir alertas
function displayAlerts(alerts) {
    const container = document.getElementById('alerts-section');
    
    if (!alerts || alerts.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-check-circle text-success mb-2"></i>
                <p>Nenhum Alerta Ativo</p>
                <small>Todos os sistemas estão funcionando normalmente!</small>
            </div>
        `;
        return;
    }
    
    let html = '';
    alerts.forEach(alert => {
        html += `
            <div class="alert-item ${alert.type}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <strong>${alert.title}</strong>
                        <p class="mb-1">${alert.message}</p>
                        <small class="text-muted">${formatTimestamp(alert.timestamp)}</small>
                    </div>
                    <span class="badge bg-${alert.type === 'warning' ? 'warning' : 'danger'}">${alert.severity}</span>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Verificar alertas
function checkAlerts() {
    fetch('/api/check-alerts')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showNotification('Alertas verificados com sucesso!', 'success');
                loadAlerts();
            }
        })
        .catch(err => {
            console.error('Erro ao verificar alertas:', err);
            showNotification('Erro ao verificar alertas', 'error');
        });
}

// Atualizar última atualização
function updateLastUpdate() {
    const now = new Date();
    document.getElementById('last-update').textContent = now.toLocaleString('pt-BR');
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

// Carregar dados ao iniciar
document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
    
    // Atualizar a cada 30 segundos
    setInterval(loadDashboardData, 30000);
}); 