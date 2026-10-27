import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import type { Row, Field } from './types';
export function Editor({ title, fields, initial = {}, onSave, onClose }: {
    title: string;
    fields: Field[];
    initial?: Row;
    onSave: (values: Row) => Promise<void>;
    onClose: () => void;
}) {
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);
    return <Dialog.Root open onOpenChange={open => { if (!open)
        onClose(); }}><Dialog.Portal><Dialog.Overlay className="overlay"/><Dialog.Content className="modal"><div className="card-heading"><Dialog.Title>{title}</Dialog.Title><Dialog.Close className="icon-button" aria-label="Close"><X /></Dialog.Close></div><Dialog.Description className="muted">Preserve source units and measurement periods. Required fields are marked *.</Dialog.Description><form onSubmit={async (e) => { e.preventDefault(); setBusy(true); setError(''); const data = new FormData(e.currentTarget); const values: Row = {}; for (const f of fields) {
        const v = data.get(f.key);
        values[f.key] = f.type === 'checkbox' ? v === 'on' : f.type === 'number' ? (v === '' ? null : Number(v)) : v;
        if (f.type === 'datetime-local' && v)
            values[f.key] = new Date(String(v)).toISOString();
    } try {
        await onSave(values);
        onClose();
    }
    catch (err) {
        setError((err as Error).message);
    }
    finally {
        setBusy(false);
    } }}><div className="form-grid">{fields.map(f => <label key={f.key} className={f.type === 'textarea' ? 'span-2' : ''}>{f.label}{f.required !== false && f.type !== 'checkbox' ? ' *' : ''}{f.options ? <select name={f.key} defaultValue={initial[f.key] ?? f.value ?? f.options[0]}>{f.options.map(o => { const value = typeof o === 'string' ? o : o.value; const label = typeof o === 'string' ? o.replaceAll('_', ' ') : o.label; return <option key={value} value={value}>{label}</option>; })}</select> : f.type === 'textarea' ? <textarea name={f.key} required={f.required !== false} defaultValue={initial[f.key] ?? f.value ?? ''} rows={3}/> : <input name={f.key} type={f.type || 'text'} step={f.type === 'number' ? 'any' : undefined} required={f.required !== false && f.type !== 'checkbox'} defaultChecked={f.type === 'checkbox' ? (initial[f.key] ?? f.value) : undefined} defaultValue={f.type === 'checkbox' ? undefined : initial[f.key] ?? f.value ?? ''}/>} {f.hint && <small>{f.hint}</small>}</label>)}</div>{error && <div role="alert" className="error">{error}</div>}<div className="form-actions"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button disabled={busy}>{busy ? 'Saving…' : 'Save record'}</button></div></form></Dialog.Content></Dialog.Portal></Dialog.Root>;
}
