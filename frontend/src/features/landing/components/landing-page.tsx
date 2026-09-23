import Image from "next/image";
import Link from "next/link";
import { ThemeToggle } from "@/shared/ui/theme-toggle";
import styles from "./landing-page.module.css";

function Arrow({ diagonal = false }: { diagonal?: boolean }) {
  return <span aria-hidden="true">{diagonal ? "↗" : "→"}</span>;
}

export function LandingPage() {
  return (
    <div className={`${styles.landing} bg-[var(--landing-bg)] text-[var(--landing-ink)]`}>
      <a className={styles.skipLink} href="#main">본문으로 건너뛰기</a>
      <header className={styles.header}>
        <Link href="/" className={styles.brand} aria-label="Metabole 첫 화면">
          <span className={`${styles.brandMark} bg-[var(--landing-accent)] text-[var(--landing-on-accent)]`} aria-hidden="true">m.</span>
          <span>Metabole<span className={`${styles.brandCaption} text-[var(--landing-muted)]`}>서울 상권 아틀라스</span></span>
        </Link>
        <nav className={styles.navigation} aria-label="주요 메뉴">
          <a href="#about" className={styles.aboutLink}>아틀라스 소개</a>
          <ThemeToggle />
          <Link href="/map" prefetch={false} className={styles.headerExplore}>지도 열기 <Arrow diagonal /></Link>
        </nav>
      </header>

      <main id="main">
        <section className={styles.hero} aria-labelledby="hero-title">
          <div className={styles.heroCopy}>
            <p className={`${styles.eyebrow} text-[var(--landing-accent)]`}><span aria-hidden="true" /> SEOUL COMMERCIAL ATLAS</p>
            <h1 id="hero-title">서울의 변화 속에서,<br />내 가게의<br /><span className="text-[var(--landing-accent)]">자리를 찾다.</span></h1>
            <p className={`${styles.heroDescription} text-[var(--landing-muted)]`}>거리마다 다른 가능성, 데이터로 한 걸음 더 가까이.<br className={styles.desktopBreak} /> 동네의 상권을 살펴보고 나만의 다음을 그려보세요.</p>
            <div className={styles.heroActions}>
              <Link href="/map" prefetch={false} className={`${styles.primaryLink} bg-[var(--landing-accent)] text-[var(--landing-on-accent)]`}>상권 탐색하기 <Arrow /></Link>
              <a href="#how-it-works" className={styles.secondaryLink}>어떻게 시작하나요? <span aria-hidden="true">↓</span></a>
            </div>
            <p className={`${styles.heroNote} text-[var(--landing-muted)]`}>서울의 동네부터, 당신의 가능성까지.</p>
          </div>

          <figure className={styles.heroVisual}>
            <div className={styles.visualHalo} aria-hidden="true" />
            <span className={`${styles.visualIndex} text-[var(--landing-muted)]`} aria-hidden="true">A NEW PERSPECTIVE<br />ON YOUR NEIGHBORHOOD</span>
            <Image className={styles.diorama} src="/landing/seoul-diorama.webp" alt="한강과 건물, 청록색 상점으로 표현한 서울의 미니어처" width={1600} height={1400} sizes="(max-width: 760px) 100vw, (max-width: 1200px) 60vw, 780px" loading="eager" fetchPriority="high" />
            <Image className={styles.locationPin} src="/landing/location-pin.webp" alt="" width={256} height={320} sizes="(max-width: 760px) 54px, 76px" />
            <div className={`${styles.visualLabel} ${styles.labelExplore} bg-[var(--landing-card)]`}><span className={`${styles.labelIcon} text-[var(--landing-accent)]`} aria-hidden="true">◎</span><span>동네를 발견하다<small className="text-[var(--landing-muted)]">행정동별 상권 탐색</small></span></div>
            <div className={`${styles.visualLabel} ${styles.labelCompare} bg-[var(--landing-card)]`}><span className={`${styles.labelIcon} text-[var(--landing-accent)]`} aria-hidden="true">▥</span><span>흐름을 읽다<small className="text-[var(--landing-muted)]">업종별 지표 비교</small></span></div>
            <div className={`${styles.visualLabel} ${styles.labelAnalysis} bg-[var(--landing-card)]`}><span className={`${styles.labelIcon} text-[var(--landing-accent)]`} aria-hidden="true">✳</span><span>가능성을 살피다<small className="text-[var(--landing-muted)]">AI 분석 리포트</small></span></div>
            <figcaption className="text-[var(--landing-muted)]">서울을 재해석한 개념 모형입니다.</figcaption>
          </figure>
        </section>

        <section id="about" className={`${styles.about} border-[var(--landing-border)]`} aria-labelledby="about-title">
          <div className={styles.sectionIntro}>
            <p className={`${styles.eyebrow} text-[var(--landing-accent)]`}>A CLOSER LOOK</p>
            <h2 id="about-title">익숙한 동네를,<br />새로운 시선으로.</h2>
          </div>
          <div className={styles.feature}>
            <span className={`${styles.featureNumber} text-[var(--landing-accent)]`}>01 / EXPLORE</span>
            <h3>지도에서 시작하는 발견</h3>
            <p className="text-[var(--landing-muted)]">궁금한 동네를 선택하고,<br />주변 상권의 모습을 살펴보세요.</p>
          </div>
          <div className={styles.feature}>
            <span className={`${styles.featureNumber} text-[var(--landing-accent)]`}>02 / COMPARE</span>
            <h3>숫자로 읽는 동네의 흐름</h3>
            <p className="text-[var(--landing-muted)]">업종과 지표를 바꾸며,<br />지역마다 다른 특징을 비교하세요.</p>
          </div>
          <div className={styles.feature}>
            <span className={`${styles.featureNumber} text-[var(--landing-accent)]`}>03 / UNDERSTAND</span>
            <h3>분석으로 넓어지는 시야</h3>
            <p className="text-[var(--landing-muted)]">선택한 지역의 AI 분석을 통해,<br />상권을 이해할 단서를 찾아보세요.</p>
          </div>
        </section>

        <section id="how-it-works" className={`${styles.howTo} bg-[var(--landing-panel)]`} aria-labelledby="how-title">
          <div>
            <p className={`${styles.eyebrow} text-[var(--landing-accent)]`}>YOUR NEXT CHAPTER</p>
            <h2 id="how-title">다음 이야기는,<br />어느 동네에서 시작될까요?</h2>
            <Link href="/map" prefetch={false} className={`${styles.textLink} text-[var(--landing-accent)]`}>나의 동네 살펴보기 <Arrow /></Link>
          </div>
          <ol className={styles.steps}>
            <li><span className="text-[var(--landing-accent)]">01</span><div><h3>궁금한 동네를 찾아보세요</h3><p className="text-[var(--landing-muted)]">지도에서 살펴보고 싶은 행정동을 선택하세요.</p></div></li>
            <li><span className="text-[var(--landing-accent)]">02</span><div><h3>나에게 필요한 지표를 고르세요</h3><p className="text-[var(--landing-muted)]">업종과 기준 연도를 설정해 상권을 비교하세요.</p></div></li>
            <li><span className="text-[var(--landing-accent)]">03</span><div><h3>분석으로 한 걸음 더 나아가세요</h3><p className="text-[var(--landing-muted)]">지역 상세 패널의 AI 분석에서 리포트를 확인하세요.</p></div></li>
          </ol>
        </section>
      </main>

      <footer className={`${styles.footer} text-[var(--landing-muted)]`}>
        <span className={`${styles.footerBrand} text-[var(--landing-ink)]`}>Metabole<span>도시의 변화, 새로운 가능성.</span></span>
        <span>SEOUL COMMERCIAL ATLAS</span>
        <a href="#main">맨 위로 <span aria-hidden="true">↑</span></a>
      </footer>
    </div>
  );
}
