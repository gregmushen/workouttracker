import { setAuthToken, getAuthToken } from '../api.js';
import { toast } from '../toast.js';
import { esc } from './utils.js';

export function renderSettings(container) {
    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">Settings</h1>
                <div class="page-subtitle">Local browser settings for this UI.</div>
            </div>
        </div>
        <div class="grid grid-2">
            <section class="card">
                <div class="card-header"><div class="card-title">Bearer Token</div></div>
                <form class="card-body" id="token-form">
                    <div class="field">
                        <label>Token</label>
                        <input class="input" name="token" type="password" value="${esc(getAuthToken())}">
                    </div>
                    <div style="display:flex;gap:8px">
                        <button class="btn btn-primary" type="submit">Save token</button>
                        <button class="btn" type="button" id="clear-token">Clear</button>
                    </div>
                </form>
            </section>
            <section class="card">
                <div class="card-header"><div class="card-title">Developer Links</div></div>
                <div class="card-body" style="display:grid;gap:10px">
                    <a class="btn" href="/openapi.json" target="_blank">OpenAPI JSON</a>
                    <a class="btn" href="/docs" target="_blank">Swagger UI</a>
                    <a class="btn" href="/redoc" target="_blank">ReDoc</a>
                </div>
            </section>
        </div>
    `;

    container.querySelector('#token-form').addEventListener('submit', event => {
        event.preventDefault();
        setAuthToken(new FormData(event.currentTarget).get('token').trim());
        toast.success('Token saved');
    });
    container.querySelector('#clear-token').addEventListener('click', () => {
        setAuthToken('');
        toast.success('Token cleared');
    });
}
