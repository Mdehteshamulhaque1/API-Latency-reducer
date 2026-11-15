"use client"

import {
  Boxes,
  Code2,
  Database,
  Layers,
  Lock,
  Workflow,
  Zap,
} from "lucide-react"

import { Reveal } from "@/components/motion/reveal"
import { cn } from "@/lib/utils"

const STACK = [
  { name: "FastAPI", icon: Zap, note: "api runtime", accent: "group-hover:text-[#00C4B4]", border: "hover:border-[#00C4B4]/50" },
  { name: "Python", icon: Code2, note: "3.11", accent: "group-hover:text-[#4B8BBE]", border: "hover:border-[#4B8BBE]/50" },
  { name: "Redis", icon: Database, note: "cache + queue", accent: "group-hover:text-[#FF4438]", border: "hover:border-[#FF4438]/50" },
  { name: "MySQL", icon: Layers, note: "relational store", accent: "group-hover:text-[#00A7E1]", border: "hover:border-[#00A7E1]/50" },
  { name: "JWT", icon: Lock, note: "auth tokens", accent: "group-hover:text-accent-cyan", border: "hover:border-accent-cyan/50" },
  { name: "SQLAlchemy", icon: Workflow, note: "async orm", accent: "group-hover:text-[#E4583C]", border: "hover:border-[#E4583C]/50" },
  { name: "Docker", icon: Boxes, note: "containerized", accent: "group-hover:text-[#2496ED]", border: "hover:border-[#2496ED]/50" },
]

export function TechStack() {
  return (
    <section className="relative pb-10 pt-4">
      <div className="container">
        <Reveal className="mb-8 flex items-center justify-center gap-2">
          <span className="mono-label">built on</span>
        </Reveal>
        <Reveal delay={0.1}>
          <div className="flex flex-wrap items-center justify-center gap-3">
            {STACK.map((item) => {
              const Icon = item.icon
              return (
                <div
                  key={item.name}
                  className={cn(
                    "group flex items-center gap-3 rounded-lg border-2 border-white/[0.08] bg-white/[0.02] px-4 py-3 transition-all duration-300 hover:-translate-y-1 hover:bg-white/[0.05] hover:shadow-brutal",
                    item.border,
                  )}
                >
                  <Icon className={cn("h-[18px] w-[18px] text-zinc-500 transition-colors group-hover:text-zinc-100", item.accent)} />
                  <div className="flex flex-col leading-tight">
                    <span className="font-mono text-[13px] text-zinc-300 transition-colors group-hover:text-white">
                      {item.name}
                    </span>
                    <span className="font-mono text-[10px] text-faint">{item.note}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </Reveal>
      </div>
    </section>
  )
}
