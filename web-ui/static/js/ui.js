// static/js/ui.js

export function getElement(id) {
    const element = document.getElementById(id);
    if (!element) {
        console.warn(`Element with id '${id}' not found`);
    }
    return element;
}

export function hideError(errorId) {
    const errorElement = getElement(errorId);
    if (errorElement) {
        errorElement.classList.add('hidden');
    }
}

export function showError(errorId, message) {
    const errorElement = getElement(errorId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove('hidden');
    }
}

export function updateStatus(message, publicIp = null) {
    const statusElement = getElement('status');
    const indicatorElement = getElement('statusIndicator');
    
    if (statusElement && message) {
        statusElement.textContent = message;
    }
    
    if (indicatorElement && message) {
        indicatorElement.classList.remove('bg-green-500', 'bg-red-500', 'bg-gray-400', 'bg-yellow-500');
        if (message.includes('Connected')) indicatorElement.classList.add('bg-green-500');
        else if (message.includes('Disconnected')) indicatorElement.classList.add('bg-red-500');
        else if (message.includes('error')) indicatorElement.classList.add('bg-red-500');
        else if (message.includes('retrying')) indicatorElement.classList.add('bg-yellow-500');
        else indicatorElement.classList.add('bg-gray-400');
    }
    
    if (publicIp) {
        const ipElement = getElement('publicIp');
        if (ipElement) ipElement.textContent = publicIp;
    }
}

export function updatePublicIp(ip) {
    const publicIpElement = getElement('publicIp');
    if (publicIpElement) {
        publicIpElement.textContent = ip;
    }
}

export function showTempMessage(message, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `fixed top-4 right-4 px-4 py-2 rounded text-white text-sm z-50 ${
        type === 'success' ? 'bg-green-500' : 'bg-red-500'
    }`;
    messageDiv.textContent = message;
    document.body.appendChild(messageDiv);
    setTimeout(() => {
        messageDiv.remove();
    }, 3000);
}

export function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}