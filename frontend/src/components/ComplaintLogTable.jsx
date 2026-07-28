import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { loadComplaintLog, resumeComplaintThread } from "../store/complaintSlice";
import RiskBadge from "./RiskBadge";

function statusPillClass(status) {
  const map = {
    Draft: "status-draft",
    "Ready to Commit": "status-ready-to-commit",
    "Under Review": "status-under-review",
    Closed: "status-closed",
  };
  return map[status] || "status-draft";
}

export default function ComplaintLogTable() {
  const dispatch = useDispatch();
  const log = useSelector((s) => s.complaints.log);
  const logStatus = useSelector((s) => s.complaints.logStatus);
  const activeComplaintId = useSelector((s) => s.complaints.activeComplaintId);

  // Refresh the log whenever the active complaint changes (new turn processed).
  useEffect(() => {
    dispatch(loadComplaintLog());
  }, [dispatch, activeComplaintId]);

  return (
    <div className="card" style={{ marginTop: 24 }}>
      <p className="section-heading">Complaint Log</p>

      {logStatus === "loading" && log.length === 0 ? (
        <div className="log-empty">Loading…</div>
      ) : log.length === 0 ? (
        <div className="log-empty">No complaints logged yet. Start a conversation with the copilot above.</div>
      ) : (
        <table className="log-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Customer</th>
              <th>Risk</th>
              <th>Status</th>
              <th>Logged</th>
            </tr>
          </thead>
          <tbody>
            {log.map((row) => (
              <tr
                key={row.id}
                onClick={() => dispatch(resumeComplaintThread(row.id))}
                title="Open this complaint's copilot thread"
              >
                <td>{row.product_name || "—"}</td>
                <td>{row.customer_name || "—"}</td>
                <td>
                  <RiskBadge level={row.risk_level} />
                </td>
                <td>
                  <span className={`status-pill ${statusPillClass(row.status)}`}>
                    <span className="dot" />
                    {row.status}
                  </span>
                </td>
                <td className="tabular">{new Date(row.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
