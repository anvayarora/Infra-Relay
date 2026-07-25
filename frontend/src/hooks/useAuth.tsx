import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, demoLogin } from '@/lib/api'

type User = { id: string; email: string; name: string; role: string }
type AuthContextValue = {
  user: User | null
  loading: boolean
  login: (email: string, password?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readStoredUser(): User | null {
  try {
    const raw = localStorage.getItem('ms_user')
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => readStoredUser())
  const [loading, setLoading] = useState(Boolean(localStorage.getItem('ms_token')))

  useEffect(() => {
    const token = localStorage.getItem('ms_token')
    if (!token) {
      setLoading(false)
      return
    }
    api.get('/auth/me')
      .then(({ data }) => {
        setUser(data.user)
        localStorage.setItem('ms_user', JSON.stringify(data.user))
      })
      .catch(() => {
        localStorage.removeItem('ms_token')
        localStorage.removeItem('ms_user')
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    async login(email: string) {
      const data = await demoLogin(email)
      setUser(data.user)
    },
    logout() {
      localStorage.removeItem('ms_token')
      localStorage.removeItem('ms_user')
      setUser(null)
      window.location.assign('/login')
    },
  }), [loading, user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
