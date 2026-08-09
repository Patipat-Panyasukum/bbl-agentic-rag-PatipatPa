import Image from "next/image";
import type { DemoProfile } from "@/lib/demo-profiles";
import { cn } from "@/lib/utils";

const AVATAR_DIMENSIONS = {
  login: 42,
  header: 36,
  card: 48,
  history: 44,
} as const;

type AvatarSize = keyof typeof AVATAR_DIMENSIONS;

export function ProfileAvatar({
  profile,
  size,
  className,
}: {
  profile: DemoProfile;
  size: AvatarSize;
  className?: string;
}) {
  const dimension = AVATAR_DIMENSIONS[size];

  return (
    <span className={cn("profile-avatar", `profile-avatar-${size}`, className)}>
      <Image
        src={profile.avatarSrc}
        alt=""
        width={dimension}
        height={dimension}
        sizes={`${dimension}px`}
      />
    </span>
  );
}
