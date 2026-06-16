import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useReducedMotion } from './useReducedMotion';

gsap.registerPlugin(ScrollTrigger);

interface ScrollRevealOptions {
  y?: number;
  x?: number;
  duration?: number;
  stagger?: number;
  ease?: string;
  start?: string;
  once?: boolean;
  scale?: number;
}

export function useScrollReveal<T extends HTMLElement>(
  options: ScrollRevealOptions = {}
) {
  const ref = useRef<T>(null);
  const reducedMotion = useReducedMotion();

  const {
    y = 40,
    x = 0,
    duration = 0.6,
    stagger = 0.08,
    ease = 'expo.out',
    start = 'top 85%',
    once = true,
    scale,
  } = options;

  useEffect(() => {
    if (reducedMotion || !ref.current) return;

    const el = ref.current;
    const children = el.children;
    if (children.length === 0) return;

    const animatables = Array.from(children);

    const fromVars: gsap.TweenVars = {
      opacity: 0,
      y,
      x,
      ...(scale !== undefined ? { scale } : {}),
    };

    const toVars: gsap.TweenVars = {
      opacity: 1,
      y: 0,
      x: 0,
      ...(scale !== undefined ? { scale: 1 } : {}),
      duration,
      stagger,
      ease,
      scrollTrigger: {
        trigger: el,
        start,
        once,
      },
    };

    gsap.fromTo(animatables, fromVars, toVars);

    return () => {
      ScrollTrigger.getAll().forEach((st) => {
        if (st.trigger === el) st.kill();
      });
    };
  }, [reducedMotion, y, x, duration, stagger, ease, start, once, scale]);

  return ref;
}
