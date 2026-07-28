const TOTAL_SEGMENTS = 10;

/** Segmented fill-level gauge showing how complete the extracted record is. */
export default function CompletenessGauge({ score = 0 }) {
  const filledSegments = Math.round((score / 100) * TOTAL_SEGMENTS);

  return (
    <div className="gauge-row">
      <div className="gauge-track" aria-hidden="true">
        {Array.from({ length: TOTAL_SEGMENTS }).map((_, i) => (
          <div key={i} className={`gauge-segment ${i < filledSegments ? "filled" : ""}`} />
        ))}
      </div>
      <span className="gauge-value tabular">{Math.round(score)}%</span>
    </div>
  );
}
