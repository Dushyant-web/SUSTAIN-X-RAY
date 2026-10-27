import React from 'react';
import { Activity, Zap } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { number, dateLabel } from './format';
import type { Row } from './types';
export function Badge({ children, tone = 'green' }: {
    children: React.ReactNode;
    tone?: string;
}) { return <span className={`badge ${tone}`}>{children}</span>; }
export function Empty({ title, children }: {
    title: string;
    children?: React.ReactNode;
}) { return <div className="empty"><Activity size={28}/><h3>{title}</h3><p>{children}</p></div>; }
export function Card({ title, sub, children, action }: {
    title: string;
    sub?: string;
    children: React.ReactNode;
    action?: React.ReactNode;
}) { return <section className="card"><div className="card-heading"><div><h2>{title}</h2>{sub && <p>{sub}</p>}</div>{action}</div>{children}</section>; }
export function Kpi({ label, value, unit, note, icon: Icon, tone = 'green' }: {
    label: string;
    value: string;
    unit?: string;
    note: string;
    icon: typeof Zap;
    tone?: string;
}) { return <div className="kpi"><div className="kpi-label">{label}<span className={`icon-box ${tone}`}><Icon size={18}/></span></div><div className="kpi-value">{value}<small>{unit}</small></div><p>{note}</p></div>; }
export function Table({ rows, columns }: {
    rows: Row[];
    columns: {
        label: string;
        render: (r: Row) => React.ReactNode;
    }[];
}) { return rows.length ? <div className="table-wrap"><table><thead><tr>{columns.map(c => <th key={c.label}>{c.label}</th>)}</tr></thead><tbody>{rows.map((r, i) => <tr key={r.id || i}>{columns.map(c => <td key={c.label}>{c.render(r)}</td>)}</tr>)}</tbody></table></div> : <Empty title="No records yet">Add validated records to populate this view.</Empty>; }
export function Trend({ bills, demand = false }: {
    bills: Row[];
    demand?: boolean;
}) { const data = bills.map(b => ({ ...b, label: dateLabel(b.period_end), mwh: b.kwh / 1000 })); return data.length ? <div className="chart"><ResponsiveContainer width="100%" height="100%">{demand ? <BarChart data={data}><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e8ece8"/><XAxis dataKey="label" tickLine={false} axisLine={false}/><YAxis tickLine={false} axisLine={false}/><Tooltip /><Bar dataKey="demand_kva" name="Recorded demand (kVA)" fill="#2e7764" radius={[6, 6, 0, 0]}/></BarChart> : <AreaChart data={data} margin={{ left: 5, right: 20, top: 20, bottom: 5 }}><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#69ae87" stopOpacity={.3}/><stop offset="100%" stopColor="#69ae87" stopOpacity={.01}/></linearGradient></defs><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e8ece8"/><XAxis dataKey="label" tickLine={false} axisLine={false}/><YAxis tickLine={false} axisLine={false} width={60}/><Tooltip formatter={(v) => [number(Number(v), 2), 'MWh']}/><Area dataKey="mwh" name="MWh" type="linear" stroke="#337e61" strokeWidth={3} fill="url(#area)" dot={{ r: 5, fill: '#fff', strokeWidth: 3 }}/></AreaChart>}</ResponsiveContainer></div> : <Empty title="Consumption history is empty">Import the reviewed historical bills or enter a bill.</Empty>; }
