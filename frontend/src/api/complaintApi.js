import axios from "axios";

// In production, set VITE_API_BASE_URL as a build-time env var instead of hardcoding.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const client = axios.create({ baseURL: BASE_URL, timeout: 60000 });

/**
 * Send one turn to the AIVOA Copilot. The backend decides which of the
 * three tools to run based on what's provided:
 *   - `file` present                          -> Document Extraction Tool
 *   - no file, `complaintId` present           -> Edit Complaint Tool
 *   - no file, no `complaintId`                -> Log Complaint Tool
 */
export function sendCopilotMessage({ message, file, complaintId }) {
  const formData = new FormData();
  if (message) formData.append("message", message);
  if (complaintId) formData.append("complaint_id", complaintId);
  if (file) formData.append("file", file);

  return client
    .post("/copilot/message", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((res) => res.data);
}

/** Fetch the complaint log (most recent first). */
export function fetchComplaints() {
  return client.get("/complaints/").then((res) => res.data);
}

/** Fetch a single complaint's full detail + chat history, to resume editing it. */
export function fetchComplaintById(id) {
  return client.get(`/complaints/${id}`).then((res) => res.data);
}
