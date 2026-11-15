/** The characters a learner can choose. Keys must match `avatars` in the learning path content. */

const INK = "#1D1B26";

interface Look {
  label: string;
  face: string;
  accent: string;
  ears: "pointed" | "round" | "tufts" | "top" | "antenna";
}

export const AVATARS: Record<string, Look> = {
  fox: { label: "Fox", face: "#FF9A4D", accent: "#FFE8D4", ears: "pointed" },
  owl: { label: "Owl", face: "#A78BFA", accent: "#EAE4FF", ears: "tufts" },
  cat: { label: "Cat", face: "#FFC83D", accent: "#FFF1CC", ears: "pointed" },
  bear: { label: "Bear", face: "#FF7FA8", accent: "#FFE0EA", ears: "round" },
  frog: { label: "Frog", face: "#4FD17F", accent: "#D9F5E3", ears: "top" },
  robot: { label: "Robot", face: "#4DA3FF", accent: "#DDEBFF", ears: "antenna" },
};

export function avatarLabel(key: string): string {
  return AVATARS[key]?.label ?? "Character";
}

function Ears({ look }: { look: Look }) {
  const common = { fill: look.face, stroke: INK, strokeWidth: 3, strokeLinejoin: "round" as const };
  switch (look.ears) {
    case "pointed":
      return (
        <>
          <path d="M14 26 L16 6 L30 16 Z" {...common} />
          <path d="M50 26 L48 6 L34 16 Z" {...common} />
        </>
      );
    case "tufts":
      return (
        <>
          <path d="M16 20 L12 8 L26 14 Z" {...common} />
          <path d="M48 20 L52 8 L38 14 Z" {...common} />
        </>
      );
    case "round":
      return (
        <>
          <circle cx="16" cy="15" r="8" {...common} />
          <circle cx="48" cy="15" r="8" {...common} />
        </>
      );
    case "top":
      return (
        <>
          <circle cx="21" cy="16" r="9" {...common} />
          <circle cx="43" cy="16" r="9" {...common} />
        </>
      );
    case "antenna":
      return (
        <>
          <path d="M32 16 V7" stroke={INK} strokeWidth={3} strokeLinecap="round" />
          <circle cx="32" cy="6" r="3.5" fill="#FFC83D" stroke={INK} strokeWidth={2.5} />
        </>
      );
  }
}

export function Avatar({ avatarKey, size = 64 }: { avatarKey: string; size?: number }) {
  const look = AVATARS[avatarKey];
  if (!look) return null;
  const robot = look.ears === "antenna";
  const frog = look.ears === "top";
  const eyeY = frog ? 16 : 31;
  const eyeX = frog ? [21, 43] : [24, 40];

  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label={look.label}>
      <Ears look={look} />
      {robot ? (
        <rect x="11" y="16" width="42" height="40" rx="12" fill={look.face} stroke={INK} strokeWidth={3} />
      ) : (
        <circle cx="32" cy="36" r="22" fill={look.face} stroke={INK} strokeWidth={3} />
      )}
      <ellipse cx="32" cy="44" rx={robot ? 13 : 12} ry={robot ? 6 : 8} fill={look.accent} stroke={INK} strokeWidth={robot ? 2.5 : 0} />
      {eyeX.map((x) => (
        <circle key={x} cx={x} cy={eyeY} r={frog ? 3.2 : 3.4} fill={INK} />
      ))}
      {robot ? (
        <path d="M26 44 H38" stroke={INK} strokeWidth={2.5} strokeLinecap="round" />
      ) : (
        <>
          {!frog && <path d="M29.5 39.5 h5 l-2.5 3 z" fill={INK} />}
          <path d={frog ? "M24 44 Q32 50 40 44" : "M27 46 Q32 50 37 46"} fill="none" stroke={INK} strokeWidth={2.5} strokeLinecap="round" />
        </>
      )}
    </svg>
  );
}
