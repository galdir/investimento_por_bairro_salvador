import React, { useEffect, useId, useRef, useState } from "react";
import { formatCompactCurrency, formatCurrency } from "../utils/formatters";

interface MonetaryValueProps {
  /** Valor numérico em Reais (BRL). */
  value: number;
  /** Quando true, compacta valores >= R$ 100 mil e expõe valor exato acessível por clique/toque/teclado. */
  compact?: boolean;
  /** Sufixo opcional exibido após o valor (ex: "/ hab"). */
  suffix?: string;
  /** Classes CSS aplicadas ao elemento principal. */
  className?: string;
  /** Test ID aplicado ao container/valor. */
  testId?: string;
  /** Tema de contraste do gatilho (para fundos escuros ou claros). */
  tone?: "light" | "dark";
  /** Alinhamento horizontal do popover de valor exato. */
  align?: "left" | "right";
}

/**
 * Exibe valores monetários com formatação compacta opcional e acesso ao valor exato por teclado e toque.
 */
export const MonetaryValue: React.FC<MonetaryValueProps> = ({
  value,
  compact = true,
  suffix = "",
  className = "",
  testId,
  tone = "light",
  align = "left",
}) => {
  const [showExact, setShowExact] = useState(false);
  const wrapperRef = useRef<HTMLSpanElement>(null);
  const popoverId = useId();

  const exactText = formatCurrency(value);
  const compactText = compact ? formatCompactCurrency(value) : exactText;
  const isCompacted = compact && compactText !== exactText;

  useEffect(() => {
    if (!showExact) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setShowExact(false);
      }
    };
    const handlePointerDown = (e: MouseEvent | TouchEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowExact(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
    };
  }, [showExact]);

  if (!isCompacted) {
    return (
      <span data-testid={testId} className={`tabular-nums ${className}`}>
        {exactText}
        {suffix}
      </span>
    );
  }

  const triggerToneClass =
    tone === "dark"
      ? "decoration-slate-400/80 hover:text-emerald-300 focus-visible:ring-emerald-400"
      : "decoration-slate-400 hover:text-emerald-700 focus-visible:ring-emerald-500";

  return (
    <span ref={wrapperRef} className="relative inline-flex items-baseline gap-1">
      <button
        type="button"
        data-testid={testId}
        aria-expanded={showExact}
        aria-controls={popoverId}
        aria-label={`${compactText}${suffix} (ver valor exato: ${exactText}${suffix})`}
        title={`Valor exato: ${exactText}${suffix}`}
        onClick={(e) => {
          e.stopPropagation();
          setShowExact((prev) => !prev);
        }}
        className={`inline-flex items-baseline gap-1 text-left tabular-nums underline decoration-dotted underline-offset-4 cursor-pointer rounded focus:outline-none focus-visible:ring-2 ${triggerToneClass} ${className}`}
      >
        <span>
          {compactText}
          {suffix}
        </span>
      </button>

      {showExact && (
        <span
          id={popoverId}
          role="status"
          data-testid={testId ? `${testId}-exato` : "valor-exato-popover"}
          onClick={(e) => e.stopPropagation()}
          className={`absolute ${align === "right" ? "right-0" : "left-0"} top-full mt-1 z-30 whitespace-nowrap rounded-lg bg-slate-900 text-white border border-slate-700 px-2.5 py-1.5 text-xs font-semibold shadow-lg tabular-nums`}
        >
          Valor exato: {exactText}
          {suffix}
        </span>
      )}
    </span>
  );
};
