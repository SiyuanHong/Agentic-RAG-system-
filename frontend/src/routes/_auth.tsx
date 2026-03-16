import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { getToken } from '@/lib/auth'

export const Route = createFileRoute('/_auth')({
  beforeLoad: () => {
    if (getToken()) {
      throw redirect({ to: '/' })
    }
  },
  component: () => (
    <div className="flex min-h-screen items-center justify-center bg-muted">
      <div className="w-full max-w-md p-4">
        <Outlet />
      </div>
    </div>
  ),
})
