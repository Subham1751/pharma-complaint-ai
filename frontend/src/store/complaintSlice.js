import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { sendCopilotMessage, fetchComplaints, fetchComplaintById } from "../api/complaintApi";

// --- Async thunks -----------------------------------------------------

/**
 * Send one turn to the copilot (text, a file, or both). The backend picks
 * the right tool (log / edit / document extraction) based on whether an
 * `activeComplaintId` is already set and whether a file is attached.
 */
export const sendMessage = createAsyncThunk(
  "complaints/sendMessage",
  async ({ message, file }, { getState, rejectWithValue }) => {
    try {
      const activeComplaintId = getState().complaints.activeComplaintId;
      return await sendCopilotMessage({ message, file, complaintId: activeComplaintId });
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

/** Load the complaint log table. */
export const loadComplaintLog = createAsyncThunk(
  "complaints/loadLog",
  async (_, { rejectWithValue }) => {
    try {
      return await fetchComplaints();
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

/** Reopen a past complaint from the log to continue its copilot thread. */
export const resumeComplaintThread = createAsyncThunk(
  "complaints/resumeThread",
  async (complaintId, { rejectWithValue }) => {
    try {
      return await fetchComplaintById(complaintId);
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

// --- Slice --------------------------------------------------------------

const initialState = {
  messages: [], // [{role: "user"|"assistant", content, attachmentName?}]
  activeComplaintId: null,
  formState: null, // current complaint record -> drives the Log Customer Complaint form
  lastChangedFields: [], // which form fields the most recent turn touched, for the "just updated" highlight
  chatStatus: "idle", // idle | loading | failed
  logStatus: "idle",
  log: [],
  error: null,
};

const complaintSlice = createSlice({
  name: "complaints",
  initialState,
  reducers: {
    /** Start a fresh complaint thread (clears the form + chat). */
    startNewComplaint(state) {
      state.messages = [];
      state.activeComplaintId = null;
      state.formState = null;
      state.lastChangedFields = [];
      state.chatStatus = "idle";
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.chatStatus = "loading";
        state.error = null;
        // Optimistically show the user's message right away.
        state.messages.push({
          role: "user",
          content: action.meta.arg.message || "",
          attachmentName: action.meta.arg.file?.name || null,
        });
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.chatStatus = "idle";
        state.formState = action.payload.complaint;
        state.activeComplaintId = action.payload.complaint.id;
        state.lastChangedFields = action.payload.changed_fields || [];
        state.messages.push({ role: "assistant", content: action.payload.assistant_reply });
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.chatStatus = "failed";
        state.error = action.payload || "The copilot couldn't process that message.";
        state.messages.push({
          role: "assistant",
          content: "Sorry, something went wrong processing that. Please try again.",
          isError: true,
        });
      })
      .addCase(loadComplaintLog.pending, (state) => {
        state.logStatus = "loading";
      })
      .addCase(loadComplaintLog.fulfilled, (state, action) => {
        state.logStatus = "succeeded";
        state.log = action.payload;
      })
      .addCase(loadComplaintLog.rejected, (state, action) => {
        state.logStatus = "failed";
        state.error = action.payload || "Failed to load complaint log.";
      })
      .addCase(resumeComplaintThread.fulfilled, (state, action) => {
        state.formState = action.payload;
        state.activeComplaintId = action.payload.id;
        state.messages = action.payload.chat_history || [];
        state.lastChangedFields = [];
      });
  },
});

export const { startNewComplaint } = complaintSlice.actions;
export default complaintSlice.reducer;
