// static/js/api.js

/**
 * Получить список всех серверов
 * @returns {Promise<Array>}
 */
export async function getServers() {
    const response = await fetch('/api/servers');
    if (!response.ok) throw new Error('Failed to fetch servers');
    return response.json();
}

/**
 * Создать новый сервер
 * @param {Object} data - данные сервера (name, port, subnet, и т.д.)
 * @returns {Promise<Object>}
 */
export async function createServer(data) {
    const response = await fetch('/api/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || `HTTP ${response.status}`);
    }
    return response.json();
}

/**
 * Удалить сервер
 * @param {string} serverId
 * @returns {Promise<void>}
 */
export async function deleteServer(serverId) {
    const response = await fetch(`/api/servers/${serverId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Delete server failed');
    return response.json();
}

/**
 * Запустить сервер
 * @param {string} serverId
 * @returns {Promise<void>}
 */
export async function startServer(serverId) {
    const response = await fetch(`/api/servers/${serverId}/start`, { method: 'POST' });
    if (!response.ok) throw new Error('Start server failed');
    return response.json();
}

/**
 * Остановить сервер
 * @param {string} serverId
 * @returns {Promise<void>}
 */
export async function stopServer(serverId) {
    const response = await fetch(`/api/servers/${serverId}/stop`, { method: 'POST' });
    if (!response.ok) throw new Error('Stop server failed');
    return response.json();
}

/**
 * Получить список клиентов сервера
 * @param {string} serverId
 * @returns {Promise<Array>}
 */
export async function getServerClients(serverId) {
    const response = await fetch(`/api/servers/${serverId}/clients`);
    if (!response.ok) throw new Error('Failed to fetch clients');
    return response.json();
}

/**
 * Получить трафик клиентов сервера
 * @param {string} serverId
 * @returns {Promise<Object>}
 */
export async function getServerTraffic(serverId) {
    const response = await fetch(`/api/servers/${serverId}/traffic`);
    if (!response.ok) return {};
    return response.json();
}

/**
 * Получить детальную информацию о сервере
 * @param {string} serverId
 * @returns {Promise<Object>}
 */
export async function getServerInfo(serverId) {
    const response = await fetch(`/api/servers/${serverId}/info`);
    if (!response.ok) throw new Error('Failed to fetch server info');
    return response.json();
}

/**
 * Получить конфигурацию сервера (raw)
 * @param {string} serverId
 * @returns {Promise<Object>}
 */
export async function getServerConfig(serverId) {
    const response = await fetch(`/api/servers/${serverId}/config`);
    if (!response.ok) throw new Error('Failed to fetch server config');
    return response.json();
}

/**
 * Скачать конфигурацию сервера (файл)
 * @param {string} serverId
 */
export function downloadServerConfig(serverId) {
    window.open(`/api/servers/${serverId}/config/download`, '_blank');
}

/**
 * Добавить клиента на сервер
 * @param {string} serverId
 * @param {Object} data - { name, apply_i_settings, i_settings }
 * @returns {Promise<Object>}
 */
export async function addClient(serverId, data) {
    const response = await fetch(`/api/servers/${serverId}/clients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || 'Failed to add client');
    }
    return response.json();
}

/**
 * Обновить I‑settings клиента
 * @param {string} serverId
 * @param {string} clientId
 * @param {Object} data
 * @returns {Promise<Object>}
 */
export async function updateClientISettings(serverId, clientId, data) {
    const response = await fetch(`/api/servers/${serverId}/clients/${clientId}/i-settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || 'Failed to update client');
    }
    return response.json();
}

/**
 * Установить время автоматической приостановки клиента
 * @param {string} serverId
 * @param {string} clientId
 * @param {string|null} suspendAtUTC - ISO строка или null
 * @returns {Promise<Object>}
 */
export async function setClientSuspendTime(serverId, clientId, suspendAtUTC) {
    const response = await fetch(`/api/servers/${serverId}/clients/${clientId}/suspend-time`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suspend_at: suspendAtUTC })
    });
    if (!response.ok) throw new Error('Failed to set suspension time');
    return response.json();
}

/**
 * Приостановить клиента
 * @param {string} serverId
 * @param {string} clientId
 * @returns {Promise<Object>}
 */
export async function suspendClient(serverId, clientId) {
    const response = await fetch(`/api/servers/${serverId}/clients/${clientId}/suspend`, {
        method: 'POST'
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || 'Suspend failed');
    }
    return response.json();
}

/**
 * Активировать клиента
 * @param {string} serverId
 * @param {string} clientId
 * @returns {Promise<Object>}
 */
export async function activateClient(serverId, clientId) {
    const response = await fetch(`/api/servers/${serverId}/clients/${clientId}/activate`, {
        method: 'POST'
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || 'Activation failed');
    }
    return response.json();
}

/**
 * Удалить клиента
 * @param {string} serverId
 * @param {string} clientId
 * @returns {Promise<Object>}
 */
export async function deleteClient(serverId, clientId) {
    const response = await fetch(`/api/servers/${serverId}/clients/${clientId}`, {
        method: 'DELETE'
    });
    if (!response.ok) throw new Error('Delete client failed');
    return response.json();
}

/**
 * Получить конфигурацию клиента (оба варианта: чистую и с комментариями)
 * @param {string} serverId
 * @param {string} clientId
 * @returns {Promise<Object>}
 */
export async function getClientConfigBoth(serverId, clientId) {
    const response = await fetch(`/api/servers/${serverId}/clients/${clientId}/config-both`);
    if (!response.ok) throw new Error('Failed to load config');
    return response.json();
}

/**
 * Скачать конфигурацию клиента (файл .conf)
 * @param {string} serverId
 * @param {string} clientId
 */
export function downloadClientConfig(serverId, clientId) {
    window.open(`/api/servers/${serverId}/clients/${clientId}/config`, '_blank');
}

/**
 * Получить системный статус (публичный IP, среда, etc.)
 * @returns {Promise<Object>}
 */
export async function getSystemStatus() {
    const response = await fetch('/api/system/status');
    if (!response.ok) throw new Error('Failed to get system status');
    return response.json();
}

/**
 * Обновить публичный IP (запросить новый)
 * @returns {Promise<Object>}
 */
export async function refreshPublicIp() {
    const response = await fetch('/api/system/refresh-ip');
    if (!response.ok) throw new Error('Failed to refresh IP');
    return response.json();
}

/**
 * Получить значения по умолчанию (MTU, subnet, port, DNS) из переменных окружения
 * @returns {Promise<Object>}
 */
export async function getDefaults() {
    const response = await fetch('/api/defaults');
    if (!response.ok) throw new Error('Failed to load defaults');
    return response.json();
}

// ---------- Логи ----------
/**
 * Получить список доступных лог-файлов
 * @returns {Promise<Array>}
 */
export async function getLogsList() {
    const response = await fetch('/api/logs/list');
    if (!response.ok) throw new Error('Failed to load logs list');
    return response.json();
}

/**
 * Получить содержимое лог-файла (последние N строк)
 * @param {string} path
 * @param {number} lines
 * @returns {Promise<Object>}
 */
export async function getLogContent(path, lines = 100) {
    const response = await fetch(`/api/logs/view?path=${encodeURIComponent(path)}&lines=${lines}`);
    if (!response.ok) throw new Error('Failed to load log content');
    return response.json();
}

/**
 * Скачать лог-файл
 * @param {string} path
 */
export function downloadLog(path) {
    window.open(`/api/logs/download?path=${encodeURIComponent(path)}`, '_blank');
}

// ---------- Дополнительные: все серверы трафик ----------
/**
 * Получить трафик интерфейсов всех серверов
 * @returns {Promise<Object>}
 */
export async function getAllServersTraffic() {
    const response = await fetch('/api/servers/traffic');
    if (!response.ok) return {};
    return response.json();
}