"use client";

import { ReactNode, UIEvent, useEffect, useRef, useState } from "react";

type F1ScrollRailProps = {
  ariaLabel: string;
  children: ReactNode;
  contentClassName?: string;
};

type ScrollState = {
  canScroll: boolean;
  left: number;
  width: number;
};

const MIN_THUMB_WIDTH = 12;

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export default function F1ScrollRail({ ariaLabel, children, contentClassName }: F1ScrollRailProps) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const [scrollState, setScrollState] = useState<ScrollState>({ canScroll: false, left: 0, width: 100 });

  function measure() {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const { clientWidth, scrollLeft, scrollWidth } = viewport;
    const canScroll = scrollWidth > clientWidth + 1;
    if (!canScroll) {
      setScrollState({ canScroll: false, left: 0, width: 100 });
      return;
    }

    const width = Math.max((clientWidth / scrollWidth) * 100, MIN_THUMB_WIDTH);
    const maxLeft = 100 - width;
    const left = maxLeft <= 0 ? 0 : (scrollLeft / (scrollWidth - clientWidth)) * maxLeft;
    setScrollState({ canScroll: true, left, width });
  }

  function scrollByPage(direction: -1 | 1) {
    const viewport = viewportRef.current;
    if (!viewport) return;
    viewport.scrollBy({ left: direction * viewport.clientWidth * 0.82, behavior: "smooth" });
  }

  function handleTrackPointer(event: React.PointerEvent<HTMLDivElement>) {
    const viewport = viewportRef.current;
    const track = event.currentTarget;
    if (!viewport || !scrollState.canScroll) return;

    const rect = track.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const thumbWidthPx = (scrollState.width / 100) * rect.width;
    const targetLeft = clamp(x - thumbWidthPx / 2, 0, rect.width - thumbWidthPx);
    const ratio = targetLeft / Math.max(rect.width - thumbWidthPx, 1);
    viewport.scrollLeft = ratio * (viewport.scrollWidth - viewport.clientWidth);
  }

  function handleThumbPointer(event: React.PointerEvent<HTMLButtonElement>) {
    const viewport = viewportRef.current;
    const track = event.currentTarget.parentElement;
    if (!viewport || !track || !scrollState.canScroll) return;

    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);

    const startX = event.clientX;
    const startScrollLeft = viewport.scrollLeft;
    const activeViewport = viewport;
    const trackWidth = track.getBoundingClientRect().width;
    const scrollable = viewport.scrollWidth - viewport.clientWidth;
    const thumbWidthPx = (scrollState.width / 100) * trackWidth;
    const trackScrollable = Math.max(trackWidth - thumbWidthPx, 1);

    function onMove(moveEvent: PointerEvent) {
      const delta = moveEvent.clientX - startX;
      activeViewport.scrollLeft = startScrollLeft + (delta / trackScrollable) * scrollable;
    }

    function onUp() {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    }

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp, { once: true });
  }

  useEffect(() => {
    measure();
    const viewport = viewportRef.current;
    if (!viewport) return;

    const observer = new ResizeObserver(measure);
    observer.observe(viewport);
    if (viewport.firstElementChild) observer.observe(viewport.firstElementChild);

    return () => observer.disconnect();
  }, [children]);

  return (
    <div className="f1-scroll-shell">
      <div
        ref={viewportRef}
        className="f1-scroll-viewport"
        aria-label={ariaLabel}
        onScroll={(event: UIEvent<HTMLDivElement>) => {
          event.currentTarget.dataset.scrolling = "true";
          measure();
        }}
      >
        <div className={contentClassName}>{children}</div>
      </div>
      <div className="f1-scroll-controls" aria-hidden={!scrollState.canScroll}>
        <button type="button" onClick={() => scrollByPage(-1)} disabled={!scrollState.canScroll}>
          <span />
        </button>
        <div className="f1-scroll-track" onPointerDown={handleTrackPointer}>
          <button
            type="button"
            className="f1-scroll-thumb"
            aria-label="Drag horizontal scroll"
            disabled={!scrollState.canScroll}
            onPointerDown={handleThumbPointer}
            style={{ left: `${scrollState.left}%`, width: `${scrollState.width}%` }}
          />
        </div>
        <button type="button" onClick={() => scrollByPage(1)} disabled={!scrollState.canScroll}>
          <span />
        </button>
      </div>
    </div>
  );
}
