import { Reveal } from "@/components/motion/reveal"
import { cn } from "@/lib/utils"

interface SectionHeadingProps {
  eyebrow: string
  title: React.ReactNode
  description?: string
  align?: "left" | "center"
  className?: string
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "center",
  className,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4",
        align === "center" && "items-center text-center",
        className,
      )}
    >
      <Reveal>
        <span className="sticker gap-2.5 bg-surface">
          {eyebrow}
        </span>
      </Reveal>
      <Reveal delay={0.08}>
        <h2 className="max-w-2xl text-balance text-[clamp(1.9rem,4vw,3.25rem)] font-bold tracking-[-0.03em] text-zinc-50">
          {title}
        </h2>
      </Reveal>
      {description && (
        <Reveal delay={0.16}>
          <p className="max-w-xl text-pretty text-[15px] leading-relaxed text-dim">
            {description}
          </p>
        </Reveal>
      )}
    </div>
  )
}
