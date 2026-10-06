"use client";

import { SOURCES } from "../lib/sources";

export function DataSourcesPage() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-5 py-10 sm:px-8">
      <h1 className="text-3xl font-semibold text-[var(--text-primary)]">데이터 출처</h1>
      <p className="mt-5 text-sm leading-7 text-[var(--text-secondary)]">
        이 서비스는 아래 공공데이터와 검색 결과를 이용합니다. 공공누리 제1유형 자료는 출처를 밝히는 조건으로 이용하며, 각 원천에서 무료로 내려받을 수 있습니다.
      </p>
      <ol className="mt-8 space-y-4">
        {SOURCES.map((source) => (
          <li key={source.dataset} className="rounded-xl border border-[var(--border)] bg-[var(--bg-surface)] p-5 sm:p-6">
            <p className="text-sm text-[var(--text-secondary)]">{source.agency}</p>
            <h2 className="mt-2 text-lg font-semibold text-[var(--text-primary)]">{source.dataset}</h2>
            <p className="mt-3 text-xs text-[var(--text-secondary)]">
              {source.koglType1 ? (
                <span className="inline-block rounded border border-[var(--border)] bg-[var(--bg-raised)] px-2 py-1">공공누리 제1유형(출처표시)</span>
              ) : source.terms}
            </p>
            {source.attribution && <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">{source.attribution}</p>}
            <ul className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm">
              {source.links.map((link) => (
                <li key={link.url}>
                  <a href={link.url} target="_blank" rel="noopener noreferrer" className="text-[var(--accent)] underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]">{link.label} ↗</a>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </main>
  );
}
