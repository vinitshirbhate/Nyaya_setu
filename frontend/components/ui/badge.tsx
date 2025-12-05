import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "secondary" | "muted";
}

export function Badge({
  className,
  variant = "primary",
  ...props
}: BadgeProps) {
  const variants: Record<BadgeProps["variant"], string> = {
    primary: "bg-primary/20 text-primary border border-primary/50",
    secondary: "bg-secondary/20 text-secondary border border-secondary/50",
    muted: "bg-slate-800 text-muted-foreground border border-border/60"
  };

  return (
    <span
      className={cn(
        "pill text-[11px] uppercase tracking-wide",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

