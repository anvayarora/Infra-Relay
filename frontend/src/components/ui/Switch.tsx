import { cn } from '../../lib/utils'

export function Switch({
  checked,
  onCheckedChange,
  label,
  description,
  disabled = false,
}: {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  label?: string
  description?: string
  disabled?: boolean
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
      <div className="min-w-0">
        {label ? <p className="text-xs font-medium">{label}</p> : null}
        {description ? (
          <p className="mt-1 text-[11px] leading-4 text-zinc-500">
            {description}
          </p>
        ) : null}
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onCheckedChange(!checked)}
        className={cn(
          'relative h-6 w-11 shrink-0 rounded-full border transition-colors disabled:cursor-not-allowed disabled:opacity-50',
          checked
            ? 'border-zinc-950 bg-zinc-950 dark:border-white dark:bg-white'
            : 'border-zinc-300 bg-zinc-200 dark:border-zinc-700 dark:bg-zinc-800',
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 h-[18px] w-[18px] rounded-full bg-white shadow-sm transition-transform dark:bg-zinc-950',
            checked ? 'translate-x-[22px]' : 'translate-x-0.5',
          )}
        />
      </button>
    </div>
  )
}
