# 🔍 Railway Environment Variable Debugging Guide

## 🚨 **Problem: OPENAI_API_KEY Set But Not Read**

You've set `OPENAI_API_KEY` in Railway Variables, but the app still says it's not set. This is a **Railway configuration issue**.

---

## ✅ **Step 1: Verify Variable Name is EXACT**

**In Railway Variables, the name MUST be exactly:**
```
OPENAI_API_KEY
```

**Common mistakes:**
- ❌ `openai_api_key` (lowercase - WRONG)
- ❌ `OpenAI_API_Key` (mixed case - WRONG)
- ❌ `OPENAI-API-KEY` (hyphens - WRONG)
- ❌ `OPENAI_API_KEY ` (trailing space - WRONG)
- ✅ `OPENAI_API_KEY` (exact uppercase - CORRECT)

---

## ✅ **Step 2: Verify Variable Value**

**The value should be:**
- Your actual OpenAI API key (starts with `sk-`)
- **NOT** the placeholder text `sk-your-actual-openai-api-key`
- **NOT** empty
- **NOT** just `sk-`

**Example of correct value:**
```
sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
```

---

## ✅ **Step 3: Check Railway Variables Tab**

1. **Go to Railway Dashboard:** https://railway.app
2. **Click your backend service**
3. **Click "Variables" tab**
4. **Look for `OPENAI_API_KEY` in the list**

**What you should see:**
```
OPENAI_API_KEY = sk-proj-... (your actual key)
```

**If you see:**
- Variable name is different → **Fix the name**
- Value is placeholder text → **Replace with real key**
- Variable doesn't exist → **Add it**

---

## ✅ **Step 4: Check Railway Logs After Redeploy**

After setting the variable, Railway will redeploy. Check the logs for:

**✅ GOOD (Variable is being read):**
```
🔍 ENVIRONMENT VARIABLES DIAGNOSTIC
  OPENAI_API_KEY: sk-proj-abc...xyz (length: 51)
🔍 SETTINGS OBJECT VALUES
  settings.OPENAI_API_KEY: SET
  settings.OPENAI_API_KEY length: 51
✅ OpenAI API key is set
```

**❌ BAD (Variable not being read):**
```
🔍 ENVIRONMENT VARIABLES DIAGNOSTIC
  OPENAI_API_KEY: NOT SET
🔍 SETTINGS OBJECT VALUES
  settings.OPENAI_API_KEY: NOT SET
❌ OPENAI_API_KEY is not set
```

---

## 🔧 **Step 5: Common Railway Issues**

### **Issue 1: Variable Set But Not Saved**

**Symptom:** You added the variable but it's not in the list
**Fix:**
1. Make sure you clicked "Save" or "Add" after entering the variable
2. Check the Variables tab again - it should appear in the list

### **Issue 2: Variable Name Has Spaces**

**Symptom:** Variable name looks right but has invisible spaces
**Fix:**
1. Delete the variable
2. Re-add it, making sure there are NO spaces before/after the name

### **Issue 3: Variable Set in Wrong Service**

**Symptom:** Variable is set but in a different service
**Fix:**
1. Make sure you're setting it in the **backend service** (not frontend or other services)
2. Check all services in your Railway project

### **Issue 4: Railway Not Redeploying**

**Symptom:** Variable is set but app hasn't restarted
**Fix:**
1. **Manually trigger redeploy:**
   - Railway Dashboard → Your Service
   - Click "Deployments" tab
   - Click "Redeploy" button
2. **Wait 3-5 minutes** for deployment to complete

---

## 🔍 **Step 6: Use Diagnostic Logs**

The code now logs diagnostic information. After redeploy, check Railway logs for:

```
🔍 ENVIRONMENT VARIABLES DIAGNOSTIC
  OPENAI_API_KEY: [value or NOT SET]
  API_KEY: [value or NOT SET]
  ...
🔍 SETTINGS OBJECT VALUES
  settings.OPENAI_API_KEY: [SET or NOT SET]
```

**This will tell you exactly what Railway is providing to the app.**

---

## ✅ **Step 7: Verify Variable Format**

**In Railway Variables tab, it should look like:**

| Variable Name | Value |
|--------------|-------|
| `OPENAI_API_KEY` | `sk-proj-abc123...` (your actual key) |

**NOT:**
- `OPENAI_API_KEY = sk-proj-...` (with `=` sign - Railway doesn't use `=`)
- `"OPENAI_API_KEY"` (with quotes - Railway doesn't use quotes)
- `OPENAI_API_KEY: sk-proj-...` (with `:` - Railway doesn't use `:`)

---

## 🚨 **If Still Not Working**

### **Option 1: Delete and Re-add Variable**

1. **In Railway Variables tab:**
   - Find `OPENAI_API_KEY`
   - Click delete/trash icon
   - Confirm deletion
2. **Add it again:**
   - Click "New Variable"
   - Name: `OPENAI_API_KEY` (exact, no spaces)
   - Value: Your actual OpenAI key (starts with `sk-`)
   - Click "Add" or "Save"
3. **Redeploy:**
   - Wait for auto-redeploy or manually trigger

### **Option 2: Check All Services**

1. **In Railway Dashboard:**
   - Check ALL services in your project
   - Make sure `OPENAI_API_KEY` is set in the **backend service**
   - Not in frontend or other services

### **Option 3: Export and Re-import**

1. **In Railway Variables tab:**
   - Some Railway UIs allow exporting variables
   - Export, verify the format, re-import

---

## 📋 **Quick Checklist**

- [ ] Variable name is exactly `OPENAI_API_KEY` (uppercase, no spaces)
- [ ] Variable value is your actual OpenAI key (starts with `sk-`)
- [ ] Variable is set in the **backend service** (not frontend)
- [ ] Variable appears in Railway Variables list
- [ ] Railway has redeployed after setting variable
- [ ] Check logs for diagnostic output
- [ ] Logs show `OPENAI_API_KEY: [your-key]` (not "NOT SET")

---

## 🎯 **Expected Log Output (After Fix)**

Once the variable is set correctly, you should see in Railway logs:

```
🔍 ENVIRONMENT VARIABLES DIAGNOSTIC
  OPENAI_API_KEY: sk-proj-abc...xyz (length: 51)
🔍 SETTINGS OBJECT VALUES
  settings.OPENAI_API_KEY: SET
  settings.OPENAI_API_KEY length: 51
✅ OpenAI API key is set
✅ ALL STARTUP VALIDATIONS PASSED
✅ Application started successfully
```

---

**The code now has diagnostic logging and fallback mechanisms. Check the Railway logs to see exactly what environment variables Railway is providing!** 🚀
