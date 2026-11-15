const INK = "#1D1B26";

interface IconProps {
  size?: number;
}

export function StarIcon({ size = 16, fill = "#fff" }: IconProps & { fill?: string }) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={INK} strokeWidth={2.2} strokeLinejoin="round">
      <path d="M12 2.8l2.8 5.8 6.4.9-4.6 4.5 1.1 6.3L12 17.3l-5.7 3 1.1-6.3L2.8 9.5l6.4-.9z" />
    </svg>
  );
}

export function LockIcon({ size = 16 }: IconProps) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.8} strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

export function ArrowIcon({ size = 18, back = false }: IconProps & { back?: boolean }) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
      <path d={back ? "M19 12H5M11 6l-6 6 6 6" : "M5 12h14M13 6l6 6-6 6"} />
    </svg>
  );
}

export function CloseIcon({ size = 18 }: IconProps) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round">
      <path d="M6 6l12 12M18 6 6 18" />
    </svg>
  );
}

export function ClockIcon({ size = 14 }: IconProps) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

export function CheckIcon({ size = 14 }: IconProps) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={INK} strokeWidth={3.6} strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12.5 10 17.5 19 7.5" />
    </svg>
  );
}

export function FlagIcon({ size = 32 }: IconProps) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={INK} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 21V4" />
      <path d="M6 4.5h11l-2.5 4 2.5 4H6Z" fill="#FF7FA8" />
    </svg>
  );
}

export function LogoIcon({ size = 32 }: IconProps) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 32 32" fill="none" stroke={INK} strokeWidth={2.5} strokeLinejoin="round">
      <path d="M16 16.5 28 22.5 16 28.5 4 22.5Z" fill="#4DA3FF" />
      <path d="M16 10 28 16 16 22 4 16Z" fill="#FF7FA8" />
      <path d="M16 3.5 28 9.5 16 15.5 4 9.5Z" fill="#FFC83D" />
    </svg>
  );
}

export function FlameIcon({ size = 16, lit = true }: IconProps & { lit?: boolean }) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill={lit ? "#FF9A4D" : "#fff"} stroke={INK} strokeWidth={2.2} strokeLinejoin="round">
      <path d="M12 2.5c.6 3.4 5.5 5.6 5.5 10.9a5.5 5.5 0 0 1-11 0c0-2 .9-3.4 2-4.6.3 1.5 1 2.4 1.9 2.8C10 8.300 10.600 5.200 12 2.500z" />
    </svg>
  );
}

export function SparkIcon({ size = 30 }: IconProps) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="#FFC83D" stroke={INK} strokeWidth={2.2} strokeLinejoin="round">
      <path d="M12 3l2.200 6.300L20.500 12l-6.300 2.700L12 21l-2.200-6.300L3.500 12l6.300-2.700z" />
    </svg>
  );
}
