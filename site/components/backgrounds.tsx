import { cn } from "@/lib/utils"

/** Fixed full-screen grain overlay. */
export function Grain() {
  return <div aria-hidden className="noise" />
}

/** Layered, slowly-drifting aurora / mesh gradient behind content. */
export function Aurora({ className }: { className?: string }) {
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      <div
        className="absolute -top-[30%] left-1/2 h-[70vh] w-[90vw] -translate-x-1/2 rounded-full opacity-[0.22] blur-[110px]"
        style={{
          background:
            "radial-gradient(closest-side, rgba(99,102,241,0.9), transparent 70%)",
        }}
      />
      <div
        className="absolute -right-[15%] top-[8%] h-[50vh] w-[45vw] rounded-full opacity-[0.16] blur-[100px]"
        style={{
          background:
            "radial-gradient(closest-side, rgba(34,211,238,0.8), transparent 70%)",
        }}
      />
      <div
        className="absolute -left-[12%] bottom-[5%] h-[45vh] w-[40vw] rounded-full opacity-[0.1] blur-[110px]"
        style={{
          background:
            "radial-gradient(closest-side, rgba(99,102,241,0.7), transparent 70%)",
        }}
      />
    </div>
  )
}

/** Faint oscilloscope grid, slowly drifting. */
export function GridBackdrop({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn(
        "bg-grid animate-grid-drift pointer-events-none absolute inset-0",
        "mask-fade-b",
        className,
      )}
    />
  )
}
