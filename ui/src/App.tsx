import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Demo from './pages/Demo'
import Chat from './pages/Chat'
import { AppShell } from './components/AppShell'

/**
 * Top-level router.
 *  /        → Landing (own navbar, full-bleed marketing layout)
 *  /demo    → Demo    (uses AppShell w/ compact header + nav tabs)
 *  /chat    → Chat    (uses AppShell)
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route element={<AppShell />}>
          <Route path="/demo" element={<Demo />} />
          <Route path="/chat" element={<Chat />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
