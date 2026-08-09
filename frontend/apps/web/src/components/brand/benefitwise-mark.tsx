import { cn } from "@/lib/utils";

export function BenefitWiseMark({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "relative grid size-10 shrink-0 place-items-center bg-[var(--ink)] text-[var(--paper)]",
        className,
      )}
    >
      <span className="font-display text-xl leading-none">B</span>
      <span className="absolute -bottom-1 -right-1 size-3 bg-[var(--saffron)]" />
    </span>
  );
}
