import { Access } from "@/components/landing/access"
import { ConsoleSections } from "@/components/landing/console-sections"
import { Footer } from "@/components/landing/footer"
import { Hero } from "@/components/landing/hero"
import { Navbar } from "@/components/landing/navbar"

export default function Home() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <ConsoleSections />
        <Access />
      </main>
      <Footer />
    </>
  )
}
