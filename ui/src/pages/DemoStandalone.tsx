import Demo from './Demo'

/**
 * Demo page WITHOUT the AppShell Header — used in blind-review mode
 * (served from the bare EC2 IP). No logo, no "BioVoyager" text, no
 * Demo/Chat tabs, no GitHub link. Just the dashboard.
 *
 * The wrapper recreates the full-height flex container that AppShell
 * normally provides, so <Demo />'s internal `flex-1` sizing still works.
 */
export default function DemoStandalone() {
  return (
    <div className="flex h-full flex-col">
      <Demo />
    </div>
  )
}
