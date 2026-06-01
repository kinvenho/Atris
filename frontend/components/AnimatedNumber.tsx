"use client";

import { useEffect, useMemo, useState } from "react";

type AnimatedNumberProps = {
  value: number;
  className?: string;
  decimals?: number;
  durationMs?: number;
  prefix?: string;
  signed?: boolean;
  suffix?: string;
};

const easeOutCubic = (value: number) => 1 - Math.pow(1 - value, 3);

export default function AnimatedNumber({
  value,
  className,
  decimals = 0,
  durationMs = 850,
  prefix = "",
  signed = false,
  suffix = "",
}: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const formatter = useMemo(
    () =>
      new Intl.NumberFormat("en", {
        maximumFractionDigits: decimals,
        minimumFractionDigits: decimals,
      }),
    [decimals],
  );

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setDisplayValue(value);
      return;
    }

    let animationFrame = 0;
    const startedAt = performance.now();
    const to = Number.isFinite(value) ? value : 0;

    const tick = (now: number) => {
      const progress = Math.min((now - startedAt) / durationMs, 1);
      setDisplayValue(to * easeOutCubic(progress));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(tick);
      }
    };

    animationFrame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationFrame);
  }, [durationMs, value]);

  const roundedValue = Number(displayValue.toFixed(decimals));
  const sign = signed && roundedValue > 0 ? "+" : "";

  return (
    <span className={className}>
      {sign}
      {prefix}
      <span className="number-roller">{formatter.format(roundedValue)}</span>
      {suffix}
    </span>
  );
}
