import { Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'
import { useAuth } from '@/hooks/useAuth'
import { AppShell } from '@/components/layout/AppShell'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { WorkflowsPage } from '@/pages/WorkflowsPage'
import { WorkflowBuilderPage } from '@/pages/WorkflowBuilderPage'
import { SandboxesPage } from '@/pages/SandboxesPage'
import { ExecutionsPage } from '@/pages/ExecutionsPage'
import { ExecutionDetailPage } from '@/pages/ExecutionDetailPage'
import { TransactionsPage } from '@/pages/TransactionsPage'
import { TransactionPage } from '@/pages/TransactionPage'
import { ResourcesPage } from '@/pages/ResourcesPage'
import { BookingsPage } from '@/pages/BookingsPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { AuditPage } from '@/pages/AuditPage'

function Protected() {
  const { user, loading } = useAuth()
  if (loading) return <div className="grid min-h-screen place-items-center text-sm text-zinc-500">Opening InfraRelay…</div>
  return user ? <AppShell /> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/transactions/:id/public" element={<TransactionPage publicMode />} />
        <Route element={<Protected />}>
          <Route index element={<DashboardPage />} />
          <Route path="workflows" element={<WorkflowsPage />} />
          <Route path="workflows/:id" element={<WorkflowBuilderPage />} />
          <Route path="sandboxes" element={<SandboxesPage />} />
          <Route path="executions" element={<ExecutionsPage />} />
          <Route path="executions/:id" element={<ExecutionDetailPage />} />
          <Route path="transactions" element={<TransactionsPage />} />
          <Route path="transactions/:id" element={<TransactionPage />} />
          <Route path="resources" element={<ResourcesPage />} />
          <Route path="bookings" element={<BookingsPage />} />
          <Route path="connections" element={<SettingsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="audit" element={<AuditPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster position="bottom-right" richColors closeButton />
    </>
  )
}
