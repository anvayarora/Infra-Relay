import { Trash2, X } from 'lucide-react'
import type { BlockDefinition, Resource } from '@/lib/types'
import { Button } from '@/components/ui/Button'
import { Input, Label, Textarea } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'

type Credential = { id: string; name: string; kind: string; active: boolean }

export function BlockInspector({
  node,
  definition,
  credentials,
  resources,
  onChange,
  onDelete,
  onClose,
}: {
  node: any
  definition?: BlockDefinition
  credentials: Credential[]
  resources: Resource[]
  onChange: (settings: any, label?: string) => void
  onDelete: () => void
  onClose: () => void
}) {
  if (!node) return null
  const settings = node.data?.settings || {}
  const set = (key: string, value: any) => onChange({ ...settings, [key]: value })

  return (
    <aside className="flex h-full w-[340px] shrink-0 flex-col border-l border-zinc-200 bg-white dark:border-zinc-900 dark:bg-zinc-950">
      <div className="flex items-start justify-between border-b border-zinc-100 p-4 dark:border-zinc-900">
        <div>
          <p className="eyebrow">Step settings</p>
          <h3 className="mt-1 text-sm font-semibold">{definition?.name || node.data?.label}</h3>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}><X size={15} /></Button>
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto p-4">
        <div className="mb-5">
          <Label>Name shown on canvas</Label>
          <Input value={node.data?.label || ''} onChange={event => onChange(settings, event.target.value)} />
        </div>
        {definition?.settings.map(field => (
          <div key={field.key} className="mb-5">
            <Label>{field.label}</Label>
            {field.type === 'textarea' || field.type === 'code' ? (
              <Textarea
                value={String(settings[field.key] ?? field.default ?? '')}
                onChange={event => set(field.key, event.target.value)}
                className={field.type === 'code' ? 'min-h-44 font-mono text-xs' : ''}
              />
            ) : field.type === 'json' ? (
              <Textarea
                key={`${node.id}-${field.key}`}
                defaultValue={JSON.stringify(settings[field.key] ?? field.default, null, 2)}
                onBlur={event => {
                  try { set(field.key, JSON.parse(event.target.value)) } catch { /* keep the last valid value */ }
                }}
                className="min-h-36 font-mono text-[11px]"
              />
            ) : field.type === 'boolean' ? (
              <button
                type="button"
                onClick={() => set(field.key, !Boolean(settings[field.key] ?? field.default))}
                className="flex w-full items-center justify-between rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800"
              >
                <span>{Boolean(settings[field.key] ?? field.default) ? 'Enabled' : 'Disabled'}</span>
                <span className={`h-5 w-9 rounded-full p-0.5 ${Boolean(settings[field.key] ?? field.default) ? 'bg-indigo-500' : 'bg-zinc-300 dark:bg-zinc-700'}`}>
                  <span className={`block h-4 w-4 rounded-full bg-white transition-transform ${Boolean(settings[field.key] ?? field.default) ? 'translate-x-4' : ''}`} />
                </span>
              </button>
            ) : field.type === 'select' ? (
              <Select
                value={String(settings[field.key] ?? field.default)}
                onValueChange={value => set(field.key, value)}
                options={(field.options || []).map(value => ({ label: value.replaceAll('_', ' '), value }))}
              />
            ) : field.type === 'credential' ? (
              <>
                <Input
                  list={`credentials-${node.id}-${field.key}`}
                  value={String(settings[field.key] ?? field.default ?? '')}
                  onChange={event => set(field.key, event.target.value)}
                  placeholder="Choose a saved connection"
                />
                <datalist id={`credentials-${node.id}-${field.key}`}>
                  {credentials.filter(item => item.active).map(item => <option key={item.id} value={item.id}>{item.name} · {item.kind}</option>)}
                </datalist>
              </>
            ) : field.type === 'resource' ? (
              <>
                <Input
                  list={`resources-${node.id}-${field.key}`}
                  value={String(settings[field.key] ?? field.default ?? '')}
                  onChange={event => set(field.key, event.target.value)}
                  placeholder="Choose a resource or use a value from an earlier step"
                />
                <datalist id={`resources-${node.id}-${field.key}`}>
                  {resources.map(resource => <option key={resource.id} value={resource.id}>{resource.name} · {resource.status}</option>)}
                </datalist>
              </>
            ) : (
              <Input
                type={field.type === 'number' ? 'number' : 'text'}
                value={String(settings[field.key] ?? field.default ?? '')}
                onChange={event => set(field.key, field.type === 'number' ? Number(event.target.value) : event.target.value)}
              />
            )}
            <p className="mt-1.5 font-mono text-[9px] text-zinc-400">{field.key}</p>
          </div>
        ))}
      </div>
      <div className="border-t border-zinc-100 p-4 dark:border-zinc-900">
        <Button variant="danger" className="w-full" onClick={onDelete}><Trash2 size={14} />Delete block</Button>
      </div>
    </aside>
  )
}
