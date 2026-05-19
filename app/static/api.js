let _onAuthRequired = null;

export function setAuthToken(token) {
    if (token) localStorage.setItem('workouttracker_token', token);
    else localStorage.removeItem('workouttracker_token');
}

export function getAuthToken() {
    return localStorage.getItem('workouttracker_token') || '';
}

export function onAuthRequired(callback) {
    _onAuthRequired = callback;
}

export async function fetchAPI(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    const token = getAuthToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    const resp = await fetch(path, {
        ...options,
        headers,
    });

    if (resp.status === 401 || resp.status === 403) {
        if (_onAuthRequired) _onAuthRequired();
        throw new Error('unauthorized');
    }

    if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${resp.status}`);
    }

    if (resp.status === 204) return null;
    const contentType = resp.headers.get('content-type') || '';
    if (contentType.includes('application/json')) return resp.json();
    return resp.text();
}

export function postAPI(path, body) {
    return fetchAPI(path, {
        method: 'POST',
        body: body !== undefined ? JSON.stringify(body) : undefined,
    });
}

export function patchAPI(path, body) {
    return fetchAPI(path, {
        method: 'PATCH',
        body: JSON.stringify(body),
    });
}

export function deleteAPI(path) {
    return fetchAPI(path, { method: 'DELETE' });
}
