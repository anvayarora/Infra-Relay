import * as DialogPrimitive from '@radix-ui/react-dialog'
import { motion } from 'framer-motion'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn, spring } from '../../lib/utils'

export function Dialog({
  open,
  onOpenChange,
  children,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: ReactNode
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      {children}
    </DialogPrimitive.Root>
  )
}

export function DialogContent({
  children,
  className,
  title,
  description,
}: {
  children: ReactNode
  className?: string
  title?: string
  description?: string
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay asChild>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-[3px]"
        />
      </DialogPrimitive.Overlay>

      <div className="pointer-events-none fixed inset-0 z-[60] grid place-items-center overflow-hidden p-4">
        <DialogPrimitive.Content asChild>
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: 6 }}
            transition={spring}
            className={cn(
              'pointer-events-auto relative flex max-h-[calc(100dvh-2rem)] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-2xl outline-none dark:border-zinc-800 dark:bg-zinc-950',
              className,
            )}
          >
            <div className="shrink-0 border-b border-zinc-100 px-5 py-4 dark:border-zinc-900">
              {title ? (
                <DialogPrimitive.Title className="pr-10 text-base font-semibold tracking-tight">
                  {title}
                </DialogPrimitive.Title>
              ) : null}

              {description ? (
                <DialogPrimitive.Description className="mt-1 max-w-2xl pr-10 text-sm leading-6 text-zinc-500">
                  {description}
                </DialogPrimitive.Description>
              ) : null}

              <DialogPrimitive.Close className="focus-ring absolute right-4 top-4 rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-950 dark:hover:bg-zinc-900 dark:hover:text-white">
                <X size={16} />
              </DialogPrimitive.Close>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5">
              {children}
            </div>
          </motion.div>
        </DialogPrimitive.Content>
      </div>
    </DialogPrimitive.Portal>
  )
}
