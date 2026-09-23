"use client";

import { useEffect } from "react";
import Link from "next/link";
import styles from "./intent-gate.module.css";

export const AUTO_NAVIGATE_MS = 1500;

interface DiagnosisLineProps {
  sentence: string;
  href: string;
  onNavigate: (href: string) => void;
}

/** 한 줄 진단. 잠시 보여주고 지도로 넘어간다 — 클릭하면 즉시. 문장은 URL에 싣지 않는다. */
export function DiagnosisLine({ sentence, href, onNavigate }: DiagnosisLineProps) {
  useEffect(() => {
    const timer = setTimeout(() => onNavigate(href), AUTO_NAVIGATE_MS);
    return () => clearTimeout(timer);
  }, [href, onNavigate]);

  return (
    <div className={styles.diagnosis} role="status">
      <p>{sentence}</p>
      <Link href={href} prefetch={false} onClick={(e) => { e.preventDefault(); onNavigate(href); }}>
        지도에서 확인 <span aria-hidden="true">→</span>
      </Link>
    </div>
  );
}
