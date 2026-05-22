import { Navbar } from '../components/landing/Navbar'
import { Hero } from '../components/landing/Hero'
import { HowItWorks } from '../components/landing/HowItWorks'
import { Metrics } from '../components/landing/Metrics'
import { InterfacePreview } from '../components/landing/InterfacePreview'
import { CTA } from '../components/landing/CTA'
import { Footer } from '../components/landing/Footer'

/**
 * / — public landing page. Marketing-style sections in order:
 * Navbar (fixed) · Hero · How it works · Metrics · Interface preview ·
 * CTA · Footer.
 */
export default function Landing() {
  return (
    <div className="min-h-full bg-white">
      <Navbar />
      <main>
        <Hero />
        <HowItWorks />
        <Metrics />
        <InterfacePreview />
        <CTA />
      </main>
      <Footer />
    </div>
  )
}
