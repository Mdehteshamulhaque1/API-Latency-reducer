import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/btn relative inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-mono text-sm font-medium tracking-tight transition-all duration-200 ease-expo focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]",
  {
    variants: {
      variant: {
        primary:
          "text-white bg-accent-gradient shadow-brutal-accent hover:shadow-brutal-accent-lg hover:brightness-110 hover:scale-[1.02]",
        outline:
          "border-2 border-white/15 bg-white/[0.02] text-zinc-200 hover:border-white/30 hover:bg-white/[0.06] hover:scale-[1.02]",
        ghost:
          "text-zinc-300 hover:bg-white/[0.06] hover:text-white hover:scale-[1.02]",
        subtle:
          "border border-white/10 bg-white/[0.03] text-zinc-300 hover:border-white/20 hover:text-white hover:scale-[1.02]",
      },
      size: {
        sm: "h-8 px-3 text-[13px]",
        md: "h-10 px-4 text-sm",
        lg: "h-11 px-5 text-sm",
      },
    },
    defaultVariants: {
      variant: "outline",
      size: "md",
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  },
)
Button.displayName = "Button"

export { Button, buttonVariants }
