"use client";

import { useEffect, useState } from "react";
import styles from "./intro-video.module.css";

export function IntroVideo() {
  const [open, setOpen] = useState(true);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open) return null;

  const close = () => setOpen(false);

  return (
    <div className={`${styles.overlay} bg-black`} role="dialog" aria-label="메타볼레 인트로 영상">
      <video
        className={styles.video}
        src="/landing/intro.mp4"
        autoPlay
        muted
        playsInline
        preload="auto"
        aria-hidden="true"
        onEnded={close}
        onError={close}
      />
      <button type="button" className={`${styles.skipButton} bg-black/60 text-white`} onClick={close}>
        건너뛰기
      </button>
    </div>
  );
}
