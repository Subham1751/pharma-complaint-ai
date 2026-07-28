/** Small colored badge for a complaint's AI-assigned risk level. */
export default function RiskBadge({ level }) {
  const normalized = (level || "Unclassified").toLowerCase();
  return (
    <span className={`risk-badge ${normalized}`}>
      <span className="dot" />
      {level || "Unclassified"}
    </span>
  );
}
