import { useMemo, useState, type DragEvent } from 'react'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { BlockIcon } from './icons'
import type { BlockDefinition } from '@/lib/types'

export function BlockPalette({ blocks, onAdd }: { blocks: BlockDefinition[]; onAdd: (block: BlockDefinition) => void }) {
  const [query, setQuery] = useState('')
  const groups = useMemo(
    () => blocks
      .filter(block => `${block.name} ${block.description} ${block.category}`.toLowerCase().includes(query.toLowerCase()))
      .reduce<Record<string, BlockDefinition[]>>((result, block) => {
        ;(result[block.category] ||= []).push(block)
        return result
      }, {}),
    [blocks, query],
  )

  function beginDrag(event: DragEvent<HTMLButtonElement>, block: BlockDefinition) {
    event.dataTransfer.setData('application/infrarelay-block', JSON.stringify(block))
    event.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <aside className="flex h-full w-[270px] shrink-0 flex-col border-r border-zinc-200 bg-white dark:border-zinc-900 dark:bg-zinc-950">
      <div className="p-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-500" />
          <Input className="pl-9 text-xs" placeholder="Find a step" value={query} onChange={event => setQuery(event.target.value)} />
        </div>
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto px-3 pb-5">
        {Object.entries(groups).map(([category, items]) => (
          <div key={category} className="mb-5">
            <div className="mb-2 px-1 text-[10px] font-semibold uppercase tracking-[.14em] text-zinc-500">{category}</div>
            <div className="space-y-1.5">
              {items.map(block => (
                <button
                  type="button"
                  draggable
                  key={block.type}
                  onDragStart={event => beginDrag(event, block)}
                  onClick={() => onAdd(block)}
                  className="group w-full cursor-grab rounded-lg border border-transparent px-2.5 py-2 text-left transition-colors hover:border-zinc-200 hover:bg-zinc-50 active:cursor-grabbing dark:hover:border-zinc-800 dark:hover:bg-zinc-900"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="grid h-7 w-7 place-items-center rounded-md border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
                      <BlockIcon name={block.icon} className="h-3.5 w-3.5" />
                    </div>
                    <div className="min-w-0">
                      <div className="truncate text-xs font-medium">{block.name}</div>
                      <div className="truncate text-[10px] text-zinc-500">{block.description}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </aside>
  )
}
