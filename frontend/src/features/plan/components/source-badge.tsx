import styles from "./plan-workspace.module.css";

/** 출처는 항상 보이고, 긴 단서는 키보드·터치로 펼쳐 읽는다. */
export function SourceBadge({ label, caveat, id }: { label: string; caveat: string; id: string }) {
  return (
    <details className={styles.source}>
      <summary data-source-badge>{label}</summary>
      <p id={id}>{caveat}</p>
    </details>
  );
}
