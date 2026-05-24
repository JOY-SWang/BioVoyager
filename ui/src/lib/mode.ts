/**
 * "Blind review" mode = served from the EC2 IP:5000 directly, bypassing
 * Cloudflare. In this mode the React app strips all branding/nav and
 * renders only the demo dashboard, so a reviewer can't see the project name,
 * authors, GitHub link, or other identifying chrome.
 *
 * Normal mode = served from the canonical Cloudflare hostname.
 */
const BLIND_REVIEW_HOSTS: ReadonlySet<string> = new Set([
  '3.148.244.109',
  '3.148.244.109:5000',
])

export function isBlindReview(): boolean {
  if (typeof window === 'undefined') return false
  return BLIND_REVIEW_HOSTS.has(window.location.host)
}
