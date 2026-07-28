import { useDispatch, useSelector } from "react-redux";
import LogComplaintForm from "./components/LogComplaintForm";
import CopilotChat from "./components/CopilotChat";
import ComplaintLogTable from "./components/ComplaintLogTable";
import { startNewComplaint } from "./store/complaintSlice";

export default function App() {
  const dispatch = useDispatch();
  const activeComplaintId = useSelector((s) => s.complaints.activeComplaintId);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-mark">Rx</div>
          <div>
            <div className="brand-title">Pharma Complaint AI</div>
            <div className="brand-subtitle">Customer Complaint Management · QMS Copilot</div>
          </div>
        </div>
        {activeComplaintId && (
          <button type="button" className="btn btn-ghost" onClick={() => dispatch(startNewComplaint())}>
            + New complaint
          </button>
        )}
      </header>

      <main className="app-body">
        <div className="workspace-grid">
          <LogComplaintForm />
          <CopilotChat />
        </div>
        <ComplaintLogTable />
      </main>
    </div>
  );
}
