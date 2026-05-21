import { Outlet } from 'react-router-dom'
import { Header } from './Header'

/**
 * AppShell — layout wrapper used for /demo and /chat.
 * The marketing landing page uses its own full-bleed Navbar instead.
 */
export function AppShell() {
  return (
    <div className="flex h-full flex-col">
      <Header />
      <Outlet />
    </div>
  )
}
