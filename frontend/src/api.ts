import { initializeApp } from 'firebase/app';
import { getAuth, signInWithEmailAndPassword, signOut } from 'firebase/auth';
const env = import.meta.env;
export const auth = env.VITE_FIREBASE_API_KEY ? getAuth(initializeApp({ apiKey: env.VITE_FIREBASE_API_KEY, authDomain: env.VITE_FIREBASE_AUTH_DOMAIN, projectId: env.VITE_FIREBASE_PROJECT_ID })) : null;
export const login = (email: string, password: string) => { if (!auth)
    throw Error('Firebase is not configured'); return signInWithEmailAndPassword(auth, email, password); };
export const logout = () => auth && signOut(auth);
export async function request(path: string, method = 'GET', body?: unknown, raw = false) {
    const token = await auth?.currentUser?.getIdToken();
    const response = await fetch(`${env.VITE_API_URL || ''}/api${path}`, { method, headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body !== undefined ? { 'Content-Type': raw ? 'text/plain' : 'application/json' } : {}) }, body: body === undefined ? undefined : raw ? String(body) : JSON.stringify(body) });
    if (!response.ok) {
        let message;
        try {
            const data = await response.json();
            message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        }
        catch {
            message = response.statusText;
        }
        throw Error(message || 'Request failed');
    }
    return response.headers.get('content-type')?.includes('text/csv') ? response.text() : response.json();
}
export function download(text: string, name: string) { const url = URL.createObjectURL(new Blob([text], { type: 'text/csv' })); const a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
