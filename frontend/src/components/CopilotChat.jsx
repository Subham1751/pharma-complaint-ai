import { useState, useRef, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendMessage } from "../store/complaintSlice";

const SUGGESTIONS = [
  {
    label: "Log a critical complaint",
    text: "Customer Priya Nair (RiverMed Pharmacy) reported dark foreign particulate matter embedded in Metformin Hydrochloride 500mg tablets, Batch MET-2201-A, 480 tablets affected. The patient reported nausea after ingestion. Received via email on 12 July 2026.",
  },
  {
    label: "Log a minor complaint",
    text: "David Coleman reported that the expiry date print is smudged on 2 of 10 boxes of Vitablend Multivitamin Softgels, Batch VTB-0987-C. No health effects, tablets and seal look normal.",
  },
];

function ChatAttachmentChip({ name }) {
  return (
    <div className="chat-attachment-chip">
      <div className="chat-attachment-icon">PDF</div>
      <span>{name}</span>
    </div>
  );
}

export default function CopilotChat() {
  const dispatch = useDispatch();
  const messages = useSelector((s) => s.complaints.messages);
  const chatStatus = useSelector((s) => s.complaints.chatStatus);
  const error = useSelector((s) => s.complaints.error);

  const [text, setText] = useState("");
  const [attachedFile, setAttachedFile] = useState(null);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatStatus]);

  function handleSend(e) {
    e.preventDefault();
    if (!text.trim() && !attachedFile) return;
    dispatch(
      sendMessage({
        message: text.trim() || undefined,
        file: attachedFile || undefined,
      }),
    );
    setText("");
    setAttachedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleSuggestion(suggestionText) {
    dispatch(sendMessage({ message: suggestionText }));
  }

  const isLoading = chatStatus === "loading";

  return (
    <div className="card copilot-card">
      <div className="copilot-header">
        <div>
          <div className="copilot-header-title-row">
            <span className="copilot-title">🧪 Sentinel</span>
          </div>
          <p className="copilot-subtitle">
            Drop complaint files or paste text below.
          </p>
        </div>
        <span className="online-dot" title="Ready" />
      </div>

      <div className="copilot-messages">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <p>
              Describe a complaint in plain language, or attach a PDF, and I'll
              fill in the form and run the risk assessment. Once a complaint is
              logged, just tell me what to change — e.g. "the batch number is
              actually BMX240602."
            </p>
            <div className="chat-suggestion-row">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.label}
                  type="button"
                  className="chip-btn"
                  onClick={() => handleSuggestion(s.text)}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i}>
              {m.attachmentName && (
                <ChatAttachmentChip name={m.attachmentName} />
              )}
              {m.content && (
                <div className={`chat-row ${m.role}`}>
                  {m.role === "assistant" && (
                    <div className="chat-avatar">AI</div>
                  )}
                  <div className={`chat-bubble ${m.isError ? "is-error" : ""}`}>
                    {m.content}
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="chat-row assistant">
            <div className="chat-avatar">AI</div>
            <div className="chat-bubble">
              <div className="typing-indicator">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="copilot-input-area">
        {error && chatStatus === "failed" && (
          <div className="error-banner">{error}</div>
        )}

        {attachedFile && (
          <div className="attached-file-preview">
            📎 {attachedFile.name}
            <button
              type="button"
              onClick={() => setAttachedFile(null)}
              aria-label="Remove attachment"
            >
              ×
            </button>
          </div>
        )}

        <form onSubmit={handleSend} className="copilot-input-row">
          <button
            type="button"
            className="icon-btn attach-btn"
            onClick={() => fileInputRef.current?.click()}
            aria-label="Attach a PDF complaint document"
            title="Attach a PDF complaint document"
          >
            📎
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            style={{ display: "none" }}
            onChange={(e) => setAttachedFile(e.target.files?.[0] || null)}
          />
          <input
            type="text"
            placeholder="Type a message or paste a complaint…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button
            type="submit"
            className="icon-btn send-btn"
            disabled={isLoading || (!text.trim() && !attachedFile)}
            aria-label="Send"
          >
            {isLoading ? "…" : "➤"}
          </button>
        </form>
      </div>
    </div>
  );
}
