export function esc(value) {
    const node = document.createElement('div');
    node.textContent = value == null ? '' : String(value);
    return node.innerHTML;
}

export function todayISO() {
    return new Date().toISOString().slice(0, 10);
}

export function fmtDate(value) {
    if (!value) return '';
    try {
        return new Date(`${value}T00:00:00`).toLocaleDateString([], {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        });
    } catch {
        return value;
    }
}

export function setSummary(set) {
    const parts = [];
    if (set.weight != null) parts.push(`${set.weight} ${set.weight_unit || ''}`);
    if (set.reps != null) parts.push(`x ${set.reps}`);
    if (set.duration_seconds != null) parts.push(`${set.duration_seconds}s`);
    if (set.distance != null) parts.push(`${set.distance} ${set.distance_unit || ''}`);
    if (set.rpe != null) parts.push(`RPE ${set.rpe}`);
    if (set.rir != null) parts.push(`RIR ${set.rir}`);
    return parts.join(' ');
}

export function renderEmpty(icon, title, hint = '') {
    return `
        <div class="empty-state">
            <span class="material-symbols-outlined">${icon}</span>
            <div class="bold">${esc(title)}</div>
            ${hint ? `<div>${esc(hint)}</div>` : ''}
        </div>
    `;
}

export function parseQuickLog(text) {
    const raw = text.trim();
    const firstSet = raw.search(/\d+(?:\.\d+)?\s*x\s*\d+/i);
    if (firstSet <= 0) return null;
    const exercise = raw.slice(0, firstSet).replace(/[,;:-]+$/, '').trim();
    const setText = raw.slice(firstSet);
    const sets = [];
    const pattern = /(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)(?:\s*(?:@|rpe\s*)(\d+(?:\.\d+)?))?(?:\s*rir\s*(\d+(?:\.\d+)?))?/gi;
    let match;
    while ((match = pattern.exec(setText))) {
        sets.push({
            weight: Number(match[1]),
            weight_unit: 'lb',
            reps: Number(match[2]),
            rpe: match[3] ? Number(match[3]) : undefined,
            rir: match[4] ? Number(match[4]) : undefined,
            set_type: 'working',
        });
    }
    if (!exercise || sets.length === 0) return null;
    return { exercise, sets };
}
