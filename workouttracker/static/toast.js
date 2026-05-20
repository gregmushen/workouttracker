let container = null;

function ensureContainer() {
    if (container) return container;
    container = document.createElement('div');
    container.className = 'toast-stack';
    document.body.appendChild(container);
    return container;
}

function show(message, type) {
    const stack = ensureContainer();
    const node = document.createElement('div');
    node.className = `toast toast-${type}`;
    node.textContent = message;
    stack.appendChild(node);
    setTimeout(() => node.remove(), 3200);
}

export const toast = {
    success(message) { show(message, 'success'); },
    error(message) { show(message, 'error'); },
    info(message) { show(message, 'info'); },
};
