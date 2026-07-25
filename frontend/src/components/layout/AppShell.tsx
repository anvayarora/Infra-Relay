import {
  useEffect,
  useState,
} from 'react'
import {
  NavLink,
  Outlet,
  useLocation,
} from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Activity,
  Boxes,
  CalendarDays,
  Cable,
  ChevronRight,
  CircleUserRound,
  FileClock,
  Gauge,
  LogOut,
  Menu,
  Moon,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  Server,
  Sun,
  Workflow,
  X,
  type LucideIcon,
} from 'lucide-react'

import {
  cn,
  spring,
} from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { useTheme } from '@/hooks/useTheme'
import { Button } from '@/components/ui/Button'

const nav: Array<{
  to: string
  label: string
  icon: LucideIcon
}> = [
  {
    to: '/',
    label: 'Overview',
    icon: Gauge,
  },
  {
    to: '/workflows',
    label: 'Automations',
    icon: Workflow,
  },
  {
    to: '/sandboxes',
    label: 'Environments',
    icon: Network,
  },
  {
    to: '/executions',
    label: 'Runs',
    icon: Activity,
  },
  {
    to: '/transactions',
    label: 'Requests',
    icon: Boxes,
  },
  {
    to: '/resources',
    label: 'Resources',
    icon: Server,
  },
  {
    to: '/bookings',
    label: 'Reservations',
    icon: CalendarDays,
  },
  {
    to: '/connections',
    label: 'Connections',
    icon: Cable,
  },
  {
    to: '/audit',
    label: 'Activity',
    icon: FileClock,
  },
]

export function AppShell() {
  const {
    user,
    logout,
  } = useAuth()

  const {
    theme,
    toggle,
  } = useTheme()

  const location = useLocation()

  const [
    sidebarOpen,
    setSidebarOpen,
  ] = useState(
    () =>
      localStorage.getItem(
        'infrarelay_sidebar',
      ) !== 'closed',
  )

  const [
    mobileOpen,
    setMobileOpen,
  ] = useState(false)

  const current = nav.find((item) =>
    item.to === '/'
      ? location.pathname === '/'
      : location.pathname.startsWith(
          item.to,
        ),
  )

  useEffect(() => {
    localStorage.setItem(
      'infrarelay_sidebar',
      sidebarOpen ? 'open' : 'closed',
    )
  }, [sidebarOpen])

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 hidden border-r border-zinc-200 bg-white transition-[width] duration-200 lg:flex lg:flex-col dark:border-zinc-900 dark:bg-zinc-950',
          sidebarOpen
            ? 'w-[248px]'
            : 'w-[72px]',
        )}
      >
        <SidebarContent
          compact={!sidebarOpen}
          user={user}
          theme={theme}
          toggleTheme={toggle}
          logout={logout}
          toggleSidebar={() =>
            setSidebarOpen(
              (open) => !open,
            )
          }
        />
      </aside>

      {mobileOpen ? (
        <>
          <button
            type="button"
            aria-label="Close navigation"
            className="fixed inset-0 z-40 bg-black/55 backdrop-blur-[2px] lg:hidden"
            onClick={() =>
              setMobileOpen(false)
            }
          />

          <motion.aside
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={spring}
            className="fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col border-r border-zinc-200 bg-white lg:hidden dark:border-zinc-900 dark:bg-zinc-950"
          >
            <SidebarContent
              compact={false}
              mobile
              user={user}
              theme={theme}
              toggleTheme={toggle}
              logout={logout}
              toggleSidebar={() =>
                setMobileOpen(false)
              }
            />
          </motion.aside>
        </>
      ) : null}

      <div
        className={cn(
          'transition-[padding] duration-200',
          sidebarOpen
            ? 'lg:pl-[248px]'
            : 'lg:pl-[72px]',
        )}
      >
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-zinc-200 bg-white/85 px-5 backdrop-blur-xl lg:px-8 dark:border-zinc-900 dark:bg-zinc-950/85">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() =>
                setMobileOpen(true)
              }
              aria-label="Open navigation"
            >
              <Menu className="h-4 w-4" />
            </Button>

            <div>
              <div className="text-xs text-zinc-500">
                Build and manage infrastructure
              </div>

              <div className="text-sm font-semibold tracking-tight">
                {current?.label || 'Workspace'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden rounded-full border border-zinc-200 px-3 py-1 text-[11px] text-zinc-500 md:inline-flex dark:border-zinc-800">
              System online
            </span>

            <Button
              variant="secondary"
              size="icon"
              className="lg:hidden"
              onClick={toggle}
            >
              {theme === 'dark' ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Moon className="h-4 w-4" />
              )}
            </Button>
          </div>
        </header>

        <motion.div
          key={location.pathname}
          initial={{
            opacity: 0,
            y: 6,
          }}
          animate={{
            opacity: 1,
            y: 0,
          }}
          transition={spring}
        >
          <Outlet />
        </motion.div>
      </div>
    </div>
  )
}

function SidebarContent({
  compact,
  mobile = false,
  user,
  theme,
  toggleTheme,
  logout,
  toggleSidebar,
}: {
  compact: boolean
  mobile?: boolean
  user:
    | {
        name?: string
        email?: string
      }
    | null
    | undefined
  theme: string
  toggleTheme: () => void
  logout: () => void
  toggleSidebar: () => void
}) {
  return (
    <>
      <div
        className={cn(
          'flex h-16 items-center border-b border-zinc-100 dark:border-zinc-900',
          compact
            ? 'justify-center px-3'
            : 'gap-3 px-5',
        )}
      >
        <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-zinc-950 text-white dark:bg-white dark:text-zinc-950">
          <Network className="h-4 w-4" />
        </div>

        {!compact ? (
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold tracking-tight">
              InfraRelay
            </div>

            <div className="truncate text-[10px] uppercase tracking-[.18em] text-zinc-500">
              Infrastructure Workspace
            </div>
          </div>
        ) : null}

        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          aria-label={
            mobile
              ? 'Close navigation'
              : compact
                ? 'Expand sidebar'
                : 'Collapse sidebar'
          }
          title={
            mobile
              ? 'Close navigation'
              : compact
                ? 'Expand sidebar'
                : 'Collapse sidebar'
          }
        >
          {mobile ? (
            <X className="h-4 w-4" />
          ) : compact ? (
            <PanelLeftOpen className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </Button>
      </div>

      <nav
        className={cn(
          'flex-1 space-y-1 overflow-y-auto py-5',
          compact ? 'px-2' : 'px-3',
        )}
      >
        {nav.map(
          ({
            to,
            label,
            icon: Icon,
          }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              title={
                compact
                  ? label
                  : undefined
              }
              className={({
                isActive,
              }) =>
                cn(
                  'group flex h-10 items-center rounded-lg text-sm text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-950 dark:hover:bg-zinc-900 dark:hover:text-white',
                  compact
                    ? 'justify-center px-2'
                    : 'gap-3 px-3',
                  isActive &&
                    'bg-zinc-100 text-zinc-950 dark:bg-zinc-900 dark:text-white',
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />

              {!compact ? (
                <span className="flex-1">
                  {label}
                </span>
              ) : null}

              {!compact ? (
                <ChevronRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-50" />
              ) : null}
            </NavLink>
          ),
        )}
      </nav>

      <div
        className={cn(
          'border-t border-zinc-200 dark:border-zinc-900',
          compact ? 'p-2' : 'p-3',
        )}
      >
        {!compact ? (
          <div className="mb-2 flex items-center gap-3 rounded-lg px-3 py-2">
            <CircleUserRound className="h-7 w-7 shrink-0 text-zinc-500" />

            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-medium">
                {user?.name}
              </div>

              <div className="truncate text-[11px] text-zinc-500">
                {user?.email}
              </div>
            </div>
          </div>
        ) : null}

        <div
          className={cn(
            'flex gap-2',
            compact && 'flex-col',
          )}
        >
          <Button
            variant="ghost"
            size={
              compact
                ? 'icon'
                : 'sm'
            }
            className={
              compact
                ? ''
                : 'flex-1 justify-start'
            }
            onClick={toggleTheme}
            title="Change theme"
          >
            {theme === 'dark' ? (
              <Sun className="h-3.5 w-3.5" />
            ) : (
              <Moon className="h-3.5 w-3.5" />
            )}

            {!compact ? 'Theme' : null}
          </Button>

          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </>
  )
}
