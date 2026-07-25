import {clsx,type ClassValue} from 'clsx';import {twMerge} from 'tailwind-merge';
export function cn(...v:ClassValue[]){return twMerge(clsx(v))}export const spring={type:'spring' as const,stiffness:300,damping:30};
export function formatDate(v?:string|null){if(!v)return '—';return new Intl.DateTimeFormat('en-GB',{dateStyle:'medium',timeStyle:'short'}).format(new Date(v))}
export function relative(v?:string|null){if(!v)return '—';const s=Math.round((new Date(v).getTime()-Date.now())/1000),a=Math.abs(s),f=new Intl.RelativeTimeFormat('en-GB',{numeric:'auto'});if(a<60)return f.format(s,'second');if(a<3600)return f.format(Math.round(s/60),'minute');if(a<86400)return f.format(Math.round(s/3600),'hour');return f.format(Math.round(s/86400),'day')}
export function getError(e:unknown){if(typeof e==='object'&&e&&'response'in e){const d=(e as any).response?.data;return d?.error||d?.details||'Request failed'}return e instanceof Error?e.message:'Request failed'}
