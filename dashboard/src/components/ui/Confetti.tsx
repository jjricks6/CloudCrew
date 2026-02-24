/**
 * Confetti animation component that rains down confetti for a few seconds.
 * Auto-cleans up after animation completes.
 */

interface ConfettiPiece {
  id: number;
  left: number;
  delay: number;
  duration: number;
  size: number;
  color: string;
}

function generateConfetti(): ConfettiPiece[] {
  const colors = ["#fbbf24", "#f87171", "#60a5fa", "#34d399", "#a78bfa", "#fb923c"];
  const pieces: ConfettiPiece[] = [];
  for (let i = 0; i < 50; i++) {
    pieces.push({
      id: i,
      left: Math.random() * 100,
      delay: Math.random() * 0.5,
      duration: 2 + Math.random() * 1,
      size: 4 + Math.random() * 6,
      color: colors[Math.floor(Math.random() * colors.length)],
    });
  }
  return pieces;
}

export function Confetti() {
  const pieces = generateConfetti();

  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden opacity-100 animate-out fade-out duration-500 delay-3000"
      style={{ zIndex: 50 }}
    >
      {pieces.map((piece) => (
        <div
          key={piece.id}
          className="absolute"
          style={{
            left: `${piece.left}%`,
            top: "-20px",
            width: `${piece.size}px`,
            height: `${piece.size}px`,
            backgroundColor: piece.color,
            borderRadius: "50%",
            animation: `fall ${piece.duration}s linear ${piece.delay}s forwards`,
          }}
        />
      ))}

      <style>{`
        @keyframes fall {
          to {
            transform: translateY(100vh) rotate(720deg);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
}
