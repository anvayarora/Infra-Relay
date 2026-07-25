import { Handle, Position, type NodeProps } from '@xyflow/react'
import { motion } from 'framer-motion'
import { MoreHorizontal } from 'lucide-react'
import { BlockIcon } from './icons'
import { cn, spring } from '@/lib/utils'
import type { BlockDefinition } from '@/lib/types'

type WorkflowNodeData = {
  label: string
  blockType: string
  settings: Record<string, unknown>
  definition?: BlockDefinition
  category?: string
  icon?: string
  accent?: string
  outputs?: string[]
}

const accents: Record<string, string> = {
  cyan: 'bg-cyan-500',
  blue: 'bg-blue-500',
  emerald: 'bg-emerald-500',
  green: 'bg-emerald-500',
  orange: 'bg-orange-500',
  violet: 'bg-violet-500',
  purple: 'bg-violet-500',
  amber: 'bg-amber-500',
  rose: 'bg-rose-500',
  indigo: 'bg-indigo-500',
  sky: 'bg-sky-500',
  zinc: 'bg-zinc-500',
}

export function WorkflowNode({ data, selected }: NodeProps) {
  const node = data as unknown as WorkflowNodeData
  const definition = node.definition
  const outputs = definition?.outputs?.length ? definition.outputs : node.outputs?.length ? node.outputs : ['main']
  const icon = definition?.icon || node.icon
  const category = definition?.category || node.category || node.blockType
  const accent = definition?.accent || node.accent || 'zinc'

  return (
    <motion.div
      layout
      transition={spring}
      className={cn(
        'relative min-w-[230px] rounded-xl border bg-white shadow-sm dark:bg-zinc-950',
        selected
          ? 'border-zinc-500 shadow-lg dark:border-zinc-500'
          : 'border-zinc-200 hover:border-zinc-300 dark:border-zinc-800 dark:hover:border-zinc-700',
      )}
    >
      <Handle type="target" position={Position.Left} />
      <div className="flex items-center gap-3 p-3.5">
        <div className="relative grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-zinc-200 dark:border-zinc-800">
          <BlockIcon name={icon} className="h-4 w-4" />
          <span className={cn('absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full ring-2 ring-white dark:ring-zinc-950', accents[accent])} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold tracking-tight">{node.label || definition?.name || node.blockType}</div>
          <div className="mt-0.5 truncate text-[11px] text-zinc-500">{category}</div>
        </div>
        <MoreHorizontal className="h-4 w-4 text-zinc-400" />
      </div>
      {outputs.length > 1 ? (
        <div className="border-t border-zinc-100 px-3 py-2 dark:border-zinc-900">
          <div className="space-y-1.5 text-right text-[10px] capitalize text-zinc-500">
            {outputs.map((output, index) => (
              <div key={output} className="relative pr-1">
                {output}
                <Handle
                  id={output}
                  type="source"
                  position={Position.Right}
                  style={{ top: 60 + index * 21 }}
                />
              </div>
            ))}
          </div>
        </div>
      ) : (
        <Handle id="main" type="source" position={Position.Right} />
      )}
    </motion.div>
  )
}
