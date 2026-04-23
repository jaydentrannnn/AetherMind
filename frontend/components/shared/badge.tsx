const badgeClassMap = {
  verified: "badge-verified",
  unverified: "badge-unverified",
  blocked: "badge-blocked",
  progress: "badge-progress",
  neutral: "badge-neutral",
} as const;

type BadgeVariant = keyof typeof badgeClassMap;

export function Badge({
  children,
  variant = "neutral",
}: {
  children: React.ReactNode;
  variant?: BadgeVariant;
}): JSX.Element {
  return <span className={`badge ${badgeClassMap[variant]}`}>{children}</span>;
}
