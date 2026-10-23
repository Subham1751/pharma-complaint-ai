import { useSelector } from "react-redux";
import RiskBadge from "./RiskBadge";
import CompletenessGauge from "./CompletenessGauge";

function statusPillClass(status) {
  const map = {
    Draft: "status-draft",
    "Ready to Commit": "status-ready-to-commit",
    "Under Review": "status-under-review",
    Closed: "status-closed",
  };
  return map[status] || "status-draft";
}

function FormField({ label, value, span2 = false, justUpdated = false }) {
  return (
    <div className={`form-field ${span2 ? "span-2" : ""}`}>
      <span className="form-field-label">{label}</span>
      <div className={`form-field-box ${!value ? "is-empty" : ""} ${justUpdated ? "just-updated" : ""}`}>
        {value || "Not provided"}
      </div>
    </div>
  );
}

export default function LogComplaintForm() {
  const complaint = useSelector((s) => s.complaints.formState);
  const lastChangedFields = useSelector((s) => s.complaints.lastChangedFields);

  // Highlight fields that were touched by the most recent copilot turn, so
  // an edit ("update the batch number") is visually obvious in the form.
  const justUpdatedFields = new Set(lastChangedFields || []);

  if (!complaint) {
    return (
      <div className="card">
        <div className="form-header">
          <div>
            <h1 className="form-title">Log Customer Complaint</h1>
            <p className="form-subtitle">API &amp; FDF Quality Assurance Module</p>
          </div>
        </div>
        <div className="form-empty-state">
          Describe a complaint or upload a document in the Sentinel panel to get started —
          this form and the risk assessment below will fill in automatically.
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="form-header">
        <div>
          <h1 className="form-title">Log Customer Complaint</h1>
          <p className="form-subtitle">API &amp; FDF Quality Assurance Module</p>
        </div>
        <span className={`status-pill ${statusPillClass(complaint.status)}`}>
          <span className="dot" />
          {complaint.status}
        </span>
      </div>

      <div className="form-section">
        <p className="form-section-title">1. Origin &amp; Customer Details</p>
        <div className="form-field-grid">
          <FormField label="Complaint Source" value={complaint.complaint_source} justUpdated={justUpdatedFields.has("complaint_source")} />
          <FormField label="Customer Name" value={complaint.customer_name} justUpdated={justUpdatedFields.has("customer_name")} />
        </div>
      </div>

      <div className="form-section">
        <p className="form-section-title">2. Product &amp; Batch Identification</p>
        <div className="form-field-grid">
          <FormField label="Product Name" value={complaint.product_name} justUpdated={justUpdatedFields.has("product_name")} />
          <FormField label="Product Strength / Grade" value={complaint.product_strength} justUpdated={justUpdatedFields.has("product_strength")} />
          <FormField label="Batch / Lot Number" value={complaint.batch_number} justUpdated={justUpdatedFields.has("batch_number")} />
          <FormField label="Affected Quantity" value={complaint.affected_quantity} justUpdated={justUpdatedFields.has("affected_quantity")} />
          <FormField label="Manufacturing Date" value={complaint.manufacturing_date} justUpdated={justUpdatedFields.has("manufacturing_date")} />
          <FormField label="Expiry Date" value={complaint.expiry_date} justUpdated={justUpdatedFields.has("expiry_date")} />
        </div>
      </div>

      <div className="form-section">
        <p className="form-section-title">3. Facility &amp; Material Impact</p>
        <div className="form-field-grid">
          <FormField label="Manufacturing Site" value={complaint.manufacturing_site} justUpdated={justUpdatedFields.has("manufacturing_site")} />
          <FormField label="Material Type" value={complaint.material_type} justUpdated={justUpdatedFields.has("material_type")} />
          <FormField label="Complaint Category" value={complaint.complaint_category} justUpdated={justUpdatedFields.has("complaint_category")} />
          <FormField label="Complaint Date" value={complaint.complaint_date} justUpdated={justUpdatedFields.has("complaint_date")} />
          <FormField
            label="Complaint Description"
            value={complaint.complaint_description}
            span2
            justUpdated={justUpdatedFields.has("complaint_description")}
          />
        </div>
      </div>

      <div className="divider" />

      <div className="risk-header">
        <p className="form-section-title" style={{ margin: 0 }}>
          AI Copilot Risk Assessment
        </p>
        <RiskBadge level={complaint.risk_level} />
      </div>
      <p className="risk-justification">{complaint.risk_justification}</p>

      {complaint.is_possible_duplicate && (
        <div className="duplicate-alert">
          ⚠ Possible duplicate of an existing complaint. {complaint.duplicate_reason}
        </div>
      )}

      <div className="divider" />

      <p className="form-field-label" style={{ marginBottom: 6 }}>
        Completeness score
      </p>
      <CompletenessGauge score={complaint.completeness_score || 0} />
      {complaint.missing_fields?.length > 0 && (
        <div className="missing-fields">
          {complaint.missing_fields.map((f) => (
            <span key={f} className="missing-chip">
              Missing: {f.replaceAll("_", " ")}
            </span>
          ))}
        </div>
      )}

      {complaint.root_cause_suggestions?.length > 0 && (
        <>
          <div className="divider" />
          <p className="form-field-label" style={{ marginBottom: 6 }}>
            Root cause suggestions
          </p>
          <ul className="rec-list">
            {complaint.root_cause_suggestions.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </>
      )}

      {complaint.capa_recommendations?.length > 0 && (
        <>
          <div className="divider" />
          <p className="form-field-label" style={{ marginBottom: 6 }}>
            CAPA recommendations
          </p>
          <ul className="rec-list">
            {complaint.capa_recommendations.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </>
      )}

      {complaint.ai_summary && (
        <>
          <div className="divider" />
          <p className="form-field-label" style={{ marginBottom: 6 }}>
            AI summary
          </p>
          <p className="summary-text">{complaint.ai_summary}</p>
        </>
      )}
    </div>
  );
}
