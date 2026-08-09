import Image from "next/image";
import { cn } from "@/lib/utils";

export function BenefitWiseLogo({
  className,
  priority = false,
}: {
  className?: string;
  priority?: boolean;
}) {
  return (
    <Image
      className={cn("benefitwise-logo", className)}
      src="/brand/benefitwise-logo.png"
      alt=""
      width={80}
      height={80}
      priority={priority}
      sizes="80px"
    />
  );
}
