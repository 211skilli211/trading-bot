/**
 * OceanBackground — Animated shader-style ocean wave background
 * Pure CSS animation (no Three.js needed) for performance on mobile.
 * Creates a subtle animated gradient that suggests ocean waves.
 * 
 * Usage:
 *   <OceanBackground /> — place as first child in a relative container
 */

export function OceanBackground({ intensity = 'subtle' as 'subtle' | 'medium' | 'strong' }) {
  const opacity = {
    subtle: 'opacity-[0.04]',
    medium: 'opacity-[0.07]',
    strong: 'opacity-[0.12]',
  }[intensity];

  return (
    <div className={`absolute inset-0 overflow-hidden pointer-events-none ${opacity}`}>
      {/* Layer 1 — Deep wave */}
      <div
        className="absolute -bottom-[20%] -left-[10%] w-[140%] h-[60%] rounded-full"
        style={{
          background: 'radial-gradient(ellipse at 30% 80%, rgba(15, 76, 117, 0.4) 0%, transparent 70%)',
          animation: 'ocean-wave-1 12s ease-in-out infinite alternate',
        }}
      />
      {/* Layer 2 — Mid wave */}
      <div
        className="absolute -bottom-[10%] -right-[10%] w-[120%] h-[50%] rounded-full"
        style={{
          background: 'radial-gradient(ellipse at 70% 70%, rgba(59, 130, 246, 0.2) 0%, transparent 60%)',
          animation: 'ocean-wave-2 15s ease-in-out infinite alternate-reverse',
        }}
      />
      {/* Layer 3 — Gold shimmer */}
      <div
        className="absolute top-[10%] left-[20%] w-[60%] h-[40%] rounded-full"
        style={{
          background: 'radial-gradient(ellipse at 50% 50%, rgba(212, 175, 55, 0.08) 0%, transparent 60%)',
          animation: 'ocean-wave-3 20s ease-in-out infinite alternate',
        }}
      />

      {/* Inline keyframes via style tag */}
      <style>{`
        @keyframes ocean-wave-1 {
          0% { transform: translateX(0) scale(1); }
          100% { transform: translateX(-3%) scale(1.02); }
        }
        @keyframes ocean-wave-2 {
          0% { transform: translateX(0) scale(1); }
          100% { transform: translateX(4%) scale(0.98); }
        }
        @keyframes ocean-wave-3 {
          0% { transform: translateY(0) scale(1); opacity: 0.5; }
          100% { transform: translateY(5%) scale(1.05); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
