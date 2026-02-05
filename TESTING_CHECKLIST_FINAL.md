# 🧪 Final Testing Checklist

## Before testing, check storage status:

Visit: `https://ai-coworker-for-businesses.fly.dev/storage-status`

**Expected output:**
```json
{
  "data_dir": "/app/data",
  "data_dir_exists": true,
  "data_dir_writable": true,
  "businesses_file_exists": true,
  "conversations_file_exists": true,
  "businesses_count": <number>,
  "conversations_count": <number>
}
```

**If `data_dir_writable: false` or files don't exist:**
- The Fly.io volume isn't working
- Run: `fly volumes list -a ai-coworker-for-businesses`
- If no volume exists, create one: `fly volumes create ai_coworker_data --size 1 -a ai-coworker-for-businesses`
- Redeploy: `fly deploy`

---

## Test Suite (Do in order)

### 1. ✅ GPT Persistence

- [ ] Create a GPT named "Test GPT 1"
- [ ] Refresh browser (F5)
- [ ] **Expected:** "Test GPT 1" still in sidebar
- [ ] Edit GPT → change name to "Test GPT 1 Renamed"
- [ ] Refresh browser
- [ ] **Expected:** Name shows as "Test GPT 1 Renamed"

**If GPT disappears:** Storage not working. Check `/storage-status`.

---

### 2. ✅ Conversation Persistence

- [ ] Click "New Chat"
- [ ] Type a message: "Hello, test message"
- [ ] **Expected:** Message appears immediately
- [ ] Wait for AI response
- [ ] **Expected:** Response appears, conversation title auto-updates to "Hello, test message..." (backend auto-titles)
- [ ] Refresh browser
- [ ] **Expected:** Conversation still in sidebar with correct title
- [ ] Click the conversation
- [ ] **Expected:** Messages still there

**If conversation disappears:** Storage not working or backend restarted without volume.

---

### 3. ✅ GPT + Chat Interaction

- [ ] Click a GPT (e.g., "Test GPT 1 Renamed")
- [ ] **Expected:** Chat interface appears immediately (either opens latest chat for that GPT or creates new one)
- [ ] **Expected:** ONLY the GPT is highlighted (red)
- [ ] Send a message
- [ ] **Expected:** Message appears instantly, then AI responds
- [ ] Look at sidebar
- [ ] **Expected:** A conversation appears (e.g., "Chat with Test GPT 1 Renamed")
- [ ] **Expected:** Both the GPT and the conversation are highlighted
- [ ] Click "New Chat"
- [ ] **Expected:** New blank chat appears, no GPT is highlighted
- [ ] Send a message in this normal chat
- [ ] **Expected:** Works (general response if no documents)

---

### 4. ✅ Upload Documents

- [ ] Click a GPT
- [ ] Upload a document (PDF/XLSX)
- [ ] **Expected:** File uploads successfully (no "Select a GPT" error)
- [ ] Refresh browser
- [ ] **Expected:** Document still attached to GPT
- [ ] Click "New Chat" (normal chat, no GPT)
- [ ] Try to upload a document
- [ ] **Expected:** Upload works (documents indexed under conversation ID)

---

### 5. ✅ Delete GPT

- [ ] Create a GPT named "Delete Me"
- [ ] Create a conversation from that GPT
- [ ] Delete the GPT
- [ ] **Expected:** GPT disappears
- [ ] **Expected:** Conversation derived from that GPT also disappears
- [ ] Refresh browser
- [ ] **Expected:** Still deleted (doesn't reappear)

---

### 6. ✅ Delete Conversation

- [ ] Create a conversation (from GPT or normal)
- [ ] Delete the conversation
- [ ] **Expected:** Conversation disappears
- [ ] **Expected:** If it was a GPT-derived conversation, the GPT remains in sidebar
- [ ] Refresh browser
- [ ] **Expected:** Conversation stays deleted

---

### 7. ✅ Message Deduplication

- [ ] Send a message
- [ ] **Expected:** User message appears ONCE (not duplicated)
- [ ] **Expected:** AI response appears ONCE (not duplicated)
- [ ] Refresh browser multiple times
- [ ] **Expected:** No duplicate messages appear

---

### 8. ✅ Multi-Sheet Excel Processing

- [ ] Upload an Excel file with multiple sheets (e.g., frameworks: "Commissioning Alliance", "Direct Payments")
- [ ] Ask: "What is the standard fee for 11 year old in Redbridge?"
- [ ] **Expected:** Correct framework/sheet is used
- [ ] **Expected:** Correct fee returned (not rounded, exact from cell)
- [ ] Ask: "What about for Merton?" (follow-up)
- [ ] **Expected:** Uses same framework (context preserved)
- [ ] Ask: "What is the solo fee for 11 year old?"
- [ ] **Expected:** Correctly distinguishes Solo from Standard (never confuses "Solo – Core" with "Core")

---

## 🚨 Critical Issues Checklist

If ANY of these fail, the app is broken:

- [ ] GPTs persist after refresh
- [ ] Conversations persist after refresh
- [ ] Clicking GPT opens chat immediately (not "Select a chat" message)
- [ ] "New Chat" creates a normal chat (no GPT highlighted)
- [ ] Uploading works in any conversation
- [ ] Deleting GPT removes it permanently (and its derived chats)
- [ ] Deleting conversation doesn't affect GPT
- [ ] Messages appear once (no duplication)
- [ ] Both GPT and conversation NOT highlighted simultaneously (unless conversation is derived from that GPT)

---

## 🔧 If Tests Fail:

### Storage not persisting:
1. Check `/storage-status` endpoint
2. Verify Fly.io volume: `fly volumes list -a ai-coworker-for-businesses`
3. Check backend logs: `fly logs -a ai-coworker-for-businesses`
4. Look for "✅ Saved X GPTs" and "✅ Conversation X persisted" logs

### 404 on conversations:
- Backend restarted and volume not mounted
- Check logs for "Storage directory not writable" errors
- Verify DATA_DIR=/app/data in environment

### Dual highlighting:
- Fixed: conversation click now syncs `selected_gpt` with `conversation.business_id`
- If still broken, check browser console for errors

### Chat field not appearing:
- Fixed: GPT click now creates/opens a chat
- If still broken, check if conversation creation returns 500 error
