import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Landing from './pages/Landing'
import Demo from './pages/Demo'
import DemoStandalone from './pages/DemoStandalone'
import Chat from './pages/Chat'
import { AppShell } from './components/AppShell'
import { isBlindReview } from './lib/mode'

/**
 * Top-level router. Two route trees, picked at boot based on the host:
 *
 * Normal mode (served via Cloudflare, biovoyager.papersearch.org):
 *   /        → Landing (full marketing page w/ Navbar)
 *   /demo    → Demo    (AppShell w/ compact Header + nav tabs)
 *   /chat    → Chat
 *
 * Blind-review mode (served via EC2 IP, 3.148.244.109:5000):
 *   /        → DemoStandalone (NO header, NO branding, NO nav)
 *   /<any>   → redirect to /
 */
export default function App() {
  const blind = isBlindReview()
  return (
    <BrowserRouter>
      <Routes>
        {blind ? (
          <>
            <Route path="/" element={<DemoStandalone />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </>
        ) : (
          <>
            <Route path="/" element={<Landing />} />
            <Route element={<AppShell />}>
              <Route path="/demo" element={<Demo />} />
              <Route path="/chat" element={<Chat />} />
            </Route>
          </>
        )}
      </Routes>
    </BrowserRouter>
  )
}
