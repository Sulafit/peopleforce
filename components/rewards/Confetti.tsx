/**
 * A short confetti fall in the level colours. Pure CSS animation: positions come from the piece's
 * index, so rendering is deterministic. Hidden entirely when the visitor prefers reduced motion.
 */
const COLORS = ["#ffc83d", "#4da3ff", "#a78bfa", "#4fd17f", "#ff9a4d", "#ff7fa8"];
const PIECES = 44;

export function Confetti() {
  return (
    <div className="confetti" aria-hidden="true">
      {Array.from({ length: PIECES }, (_, index) => (
        <span
          key={index}
          className={`confetti__piece${index % 3 === 0 ? " confetti__piece--round" : ""}`}
          style={
            {
              left: `${(index * 37 + 11) % 100}%`,
              background: COLORS[index % COLORS.length],
              "--drift": `${((index * 53) % 160) - 80}px`,
              "--spin": `${360 + ((index * 97) % 540)}deg`,
              animationDelay: `${(index % 11) * 0.06}s`,
              animationDuration: `${1.9 + (index % 5) * 0.28}s`,
            } as React.CSSProperties
          }
        />
      ))}
    </div>
  );
}
