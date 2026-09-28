import { ReactNode } from "react";

export type IconName = "anchor" | "bell" | "crosshair" | "droplet" | "layers" | "radar" | "route" | "satellite" | "shield" | "spark" | "vessel" | "download";

export function Icon({ name, className = "size-5" }: { name: IconName; className?: string }) {
  const paths: Record<IconName, ReactNode> = {
    anchor: <><path d="M12 22V8" /><path d="M5 12H2a10 10 0 0 0 20 0h-3" /><circle cx="12" cy="5" r="3" /></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
    crosshair: <><circle cx="12" cy="12" r="7" /><path d="M12 2v4m0 12v4M2 12h4m12 0h4" /></>,
    droplet: <path d="M12 2S5 10 5 15a7 7 0 0 0 14 0c0-5-7-13-7-13Z" />,
    layers: <><path d="m12 2 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5M3 17l9 5 9-5" /></>,
    radar: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4" /><path d="m12 12 6-6M3 12h2m14 0h2M12 3v2m0 14v2" /></>,
    route: <><circle cx="6" cy="18" r="2" /><circle cx="18" cy="6" r="2" /><path d="M8 18c6 0 2-12 8-12" /></>,
    satellite: <><path d="m13 7 4-4 4 4-4 4-4-4ZM3 17l4-4 4 4-4 4-4-4Z" /><path d="m11 13 2-2M5 5a14 14 0 0 1 14 14M5 9a10 10 0 0 1 10 10" /></>,
    shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />,
    spark: <path d="m12 2 1.6 5.1L19 9l-5.4 1.9L12 16l-1.6-5.1L5 9l5.4-1.9L12 2Z" />,
    vessel: <><path d="m3 14 2 6h14l2-6-9-4-9 4Z" /><path d="M8 11V6h8v5M12 6V3M2 22c2-1 4-1 6 0 2-1 4-1 6 0 2-1 4-1 6 0" /></>,
    download: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></>,
  };
  return (
    <svg
      className={`inline-block shrink-0 ${className}`}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

export function Micro({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <span className={`font-mono text-micro uppercase tracking-command ${className}`}>{children}</span>;
}

export function Action({
  children,
  active = false,
  className = "",
  style,
  onClick,
}: {
  children: ReactNode;
  active?: boolean;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
}) {
  return (
    <span
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(event) => event.key === "Enter" && onClick?.()}
      style={style}
      className={`inline-flex cursor-pointer select-none items-center justify-center transition-all focus:outline-none focus:ring-2 focus:ring-tide ${
        active ? "bg-tide text-night" : "text-fog hover:bg-white/5 hover:text-white"
      } ${className}`}
    >
      {children}
    </span>
  );
}

