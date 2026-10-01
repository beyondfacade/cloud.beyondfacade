import type { ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import { AccountMenu } from "@/shared/ui/account-menu";
import { ThemeToggle } from "@/shared/ui/theme-toggle";
import styles from "./landing-page.module.css";

function Arrow({ diagonal = false }: { diagonal?: boolean }) {
  return <span aria-hidden="true">{diagonal ? "↗" : "→"}</span>;
}

interface LandingPageProps {
  /** 히어로 카피 아래 슬롯 — 관문 입력창이 여기 들어온다. 조립은 app/page.tsx가 한다 (feature 간 직접 import 금지). */
  hero?: ReactNode;
}

export function LandingPage({ hero }: LandingPageProps = {}) {
  return (
    <div className={`${styles.landing} bg-[var(--landing-bg)] text-[var(--landing-ink)]`}>
      <a className={styles.skipLink} href="#main">본문으로 건너뛰기</a>
      <header className={styles.header}>
        <Link href="/" className={styles.brand} aria-label="Metabole 첫 화면">
          <span className={`${styles.brandMark} bg-[var(--landing-accent)] text-[var(--landing-on-accent)]`} aria-hidden="true">m.</span>
          <span>Metabole<span className={`${styles.brandCaption} text-[var(--landing-muted)]`}>서울 상권 메타볼레</span></span>
        </Link>
        <nav className={styles.navigation} aria-label="주요 메뉴">
          <a href="#about" className={styles.aboutLink}>메타볼레 소개</a>
          <AccountMenu />
          <ThemeToggle />
          <Link href="/map" prefetch={false} className={styles.headerExplore}>경고 지도 <Arrow diagonal /></Link>
        </nav>
      </header>

      <main id="main">
        <section className={styles.hero} aria-labelledby="hero-title">
          <div className={styles.heroCopy}>
            <p className={`${styles.eyebrow} text-[var(--landing-accent)]`}><span aria-hidden="true" /> SEOUL COMMERCIAL METABOLE</p>
            <h1 id="hero-title">가게 자리를 찾기 전에,<br />피해야 할 자리부터<br /><span className="text-[var(--landing-accent)]">확인하세요.</span></h1>
            <p className={`${styles.heroDescription} text-[var(--landing-muted)]`}>서울 427개 동, 12개 업종. 문 닫은 가게의 기록으로 창업 경고를 판정합니다.<br className={styles.desktopBreak} /> 좋은 곳을 추천하지 않습니다. 나쁜 조합을 먼저 걸러 드립니다.</p>
            {hero}
            <div className={styles.heroActions}>
              <Link href="/map" prefetch={false} className={`${styles.primaryLink} bg-[var(--landing-accent)] text-[var(--landing-on-accent)]`}>창업 경고 지도 보기 <Arrow /></Link>
              <a href="#about" className={styles.secondaryLink}>어떻게 판정하나요? <span aria-hidden="true">↓</span></a>
            </div>
            <p className={`${styles.heroNote} text-[var(--landing-muted)]`}>모든 판정에는 근거 수치와 출처가 붙습니다.</p>
          </div>

          <figure className={styles.heroVisual}>
            <div className={styles.visualHalo} aria-hidden="true" />
            <span className={`${styles.visualIndex} text-[var(--landing-muted)]`} aria-hidden="true">CHECK BEFORE<br />YOU SIGN</span>
            <Image className={styles.diorama} src="/landing/seoul-diorama.webp" alt="한강과 건물, 청록색 상점으로 표현한 서울의 미니어처" width={1600} height={1400} sizes="(max-width: 760px) 100vw, (max-width: 1200px) 60vw, 780px" loading="eager" fetchPriority="high" />
            <Image className={styles.locationPin} src="/landing/location-pin.webp" alt="" width={256} height={320} sizes="(max-width: 760px) 54px, 76px" />
            <div className={`${styles.visualLabel} ${styles.labelExplore} bg-[var(--landing-card)]`}><span className={`${styles.labelIcon} text-[var(--landing-accent)]`} aria-hidden="true">◎</span><span>경고를 확인하다<small className="text-[var(--landing-muted)]">동×업종 창업 경고 판정</small></span></div>
            <div className={`${styles.visualLabel} ${styles.labelCompare} bg-[var(--landing-card)]`}><span className={`${styles.labelIcon} text-[var(--landing-accent)]`} aria-hidden="true">▥</span><span>이유를 읽다<small className="text-[var(--landing-muted)]">신호별 근거와 출처</small></span></div>
            <div className={`${styles.visualLabel} ${styles.labelAnalysis} bg-[var(--landing-card)]`}><span className={`${styles.labelIcon} text-[var(--landing-accent)]`} aria-hidden="true">✳</span><span>대안을 찾다<small className="text-[var(--landing-muted)]">다른 동네 · 다른 업종</small></span></div>
            <figcaption className="text-[var(--landing-muted)]">서울을 재해석한 개념 모형입니다.</figcaption>
          </figure>
        </section>

        <section id="about" className={`${styles.about} border-[var(--landing-border)]`} aria-labelledby="about-title">
          <div className={styles.sectionIntro}>
            <p className={`${styles.eyebrow} text-[var(--landing-accent)]`}>WHAT WE TELL YOU</p>
            <h2 id="about-title">좋은 곳은 말하지 않습니다.<br />피해야 할 곳을 말합니다.</h2>
          </div>
          <div className={styles.feature}>
            <span className={`${styles.featureNumber} text-[var(--landing-accent)]`}>01 / VERDICT</span>
            <h3>판정은 셋 중 하나</h3>
            <p className="text-[var(--landing-muted)]">비추천 · 조건부 · 경고 없음.<br />추천 등급은 없고, 표본이 부족하면 판정을 보류합니다.</p>
          </div>
          <div className={styles.feature}>
            <span className={`${styles.featureNumber} text-[var(--landing-accent)]`}>02 / EVIDENCE</span>
            <h3>과거로 돌아가 검증했습니다</h3>
            <p className="text-[var(--landing-muted)]">2022년 6월 데이터로 판정한 뒤 실제 폐업과 대조했습니다. 카페는 비추천 동에서 76.8%, 경고 없음 동에서 38.2%가 3년 안에 문을 닫았습니다. 음식 업종은 차이가 작아 참고로만 보세요.</p>
          </div>
          <div className={styles.feature}>
            <span className={`${styles.featureNumber} text-[var(--landing-accent)]`}>03 / WHAT NEXT</span>
            <h3>그래도 한다면</h3>
            <p className="text-[var(--landing-muted)]">대안 동네와 업종, 필요 자금, 지원사업,<br />상담 준비자료까지 이어집니다.</p>
          </div>
        </section>

        <section id="how-it-works" className={`${styles.howTo} bg-[var(--landing-panel)]`} aria-labelledby="how-title">
          <div>
            <p className={`${styles.eyebrow} text-[var(--landing-accent)]`}>BEFORE YOU SIGN</p>
            <h2 id="how-title">계약서에 도장 찍기 전에,<br />한 번만 확인하세요.</h2>
            <Link href="/map" prefetch={false} className={`${styles.textLink} text-[var(--landing-accent)]`}>내 후보지 확인하기 <Arrow /></Link>
          </div>
          <ol className={styles.steps}>
            <li><span className="text-[var(--landing-accent)]">01</span><div><h3>동네와 업종을 한 문장으로 적으세요</h3><p className="text-[var(--landing-muted)]">예: 역삼동에 카페, 예산 5천.</p></div></li>
            <li><span className="text-[var(--landing-accent)]">02</span><div><h3>판정과 대안을 확인하세요</h3><p className="text-[var(--landing-muted)]">켜진 경고 신호와 근거, 굳이 한다면 갈 만한 다른 동네와 업종을 봅니다.</p></div></li>
            <li><span className="text-[var(--landing-accent)]">03</span><div><h3>리포트와 자금 계획으로 이어가세요</h3><p className="text-[var(--landing-muted)]">왜 안 되는지, 얼마가 필요한지, 상담에 무엇을 들고 갈지 정리합니다.</p></div></li>
          </ol>
        </section>
      </main>

      <footer className={`${styles.footer} text-[var(--landing-muted)]`}>
        <span className={`${styles.footerBrand} text-[var(--landing-ink)]`}>Metabole<span>문 닫은 가게의 기록에서 배웁니다.</span></span>
        <span>SEOUL COMMERCIAL METABOLE</span>
        <a href="#main">맨 위로 <span aria-hidden="true">↑</span></a>
      </footer>
    </div>
  );
}
