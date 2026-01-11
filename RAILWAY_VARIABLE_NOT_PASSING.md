# 🚨 CRITICAL: Railway Not Passing Environment Variables

## **The Problem**

You've set `OPENAI_API_KEY` in Railway Variables, but the app logs show:
```
❌ OPENAI_API_KEY not found in environment variables
```

**This means Railway is NOT passing the variable to your container.**

---

## ✅ **Step 1: Verify Variable is Set Correctly**

### **In Railway Dashboard:**

1. **Go to:** https://railway.app
2. **Click your backend service** (not the project, the SERVICE)
3. **Click "Variables" tab**
4. **Look for `OPENAI_API_KEY` in the list**

**What you should see:**
```
OPENAI_API_KEY = sk-proj-... (your actual key)
```

**If you DON'T see it:**
- The variable wasn't saved
- You're looking at the wrong service
- Variable name has a typo

---

## ✅ **Step 2: Check Which Service Has the Variable**

**Railway has TWO levels:**
1. **Project-level variables** (shared across services)
2. **Service-level variables** (specific to one service)

**Your backend service needs the variable at the SERVICE level.**

### **How to Check:**

1. **In Railway Dashboard:**
   - Click your **backend service** (the one that runs the FastAPI app)
   - Click "Variables" tab
   - Look for `OPENAI_API_KEY`

2. **If it's not there:**
   - Check if it's at the **project level** instead
   - Project-level variables might not be passed to services
   - **Move it to the service level**

---

## ✅ **Step 3: Delete and Re-add Variable**

**Sometimes Railway caches variables incorrectly:**

1. **In Railway Variables tab:**
   - Find `OPENAI_API_KEY`
   - **Delete it** (click trash icon)
   - **Confirm deletion**

2. **Add it again:**
   - Click "New Variable" (or "Add Variable")
   - **Name:** Type `OPENAI_API_KEY` exactly (don't copy-paste, type it)
   - **Value:** Paste your actual OpenAI key (starts with `sk-`)
   - **Make sure you're adding it to the BACKEND SERVICE** (not project)
   - Click "Add" or "Save"

3. **Verify:**
   - The variable should appear in the list
   - Name should be exactly `OPENAI_API_KEY` (no spaces, all uppercase)

---

## ✅ **Step 4: Force Redeploy**

**After setting the variable:**

1. **Railway should auto-redeploy** (wait 2-3 minutes)
2. **OR manually redeploy:**
   - Railway Dashboard → Your Service
   - Click "Deployments" tab
   - Click "Redeploy" button
   - Wait 3-5 minutes

---

## 🔍 **Step 5: Check Diagnostic Logs**

**After redeploy, the new code will log ALL environment variables.**

**Look for this in Railway logs:**
```
🔍 ENVIRONMENT VARIABLES DIAGNOSTIC - ALL VARIABLES
🔍 Found OpenAI/API related variables:
  OPENAI_API_KEY: sk-proj-... (length: 51)
```

**If you see:**
```
⚠️  No OpenAI/API related variables found in environment!
```

**This confirms Railway is NOT passing the variable.**

---

## 🚨 **Step 6: Common Railway Issues**

### **Issue 1: Variable Set in Wrong Service**

**Symptom:** Variable exists but in frontend service, not backend
**Fix:** Set it in the **backend service** specifically

### **Issue 2: Variable Set at Project Level**

**Symptom:** Variable exists at project level but not service level
**Fix:** Railway sometimes doesn't pass project-level vars to services. Set it at **service level**.

### **Issue 3: Variable Name Has Typo**

**Symptom:** Variable name looks right but has invisible character
**Fix:** Delete and re-type the name exactly: `OPENAI_API_KEY`

### **Issue 4: Variable Not Saved**

**Symptom:** You added it but it's not in the list
**Fix:** Make sure you clicked "Save" or "Add" button

### **Issue 5: Railway Bug/Cache**

**Symptom:** Variable is set but still not passed
**Fix:** 
1. Delete ALL variables
2. Redeploy
3. Re-add variables one by one
4. Redeploy again

---

## ✅ **Step 7: Verify Variable Format**

**In Railway Variables, it should look like:**

| Variable Name | Value |
|--------------|-------|
| `OPENAI_API_KEY` | `sk-proj-abc123...xyz` |

**NOT:**
- `OPENAI_API_KEY = sk-...` (with `=` sign)
- `"OPENAI_API_KEY"` (with quotes)
- `OPENAI_API_KEY: sk-...` (with `:`)
- `OPENAI_API_KEY ` (with trailing space)

---

## 🔍 **Step 8: Check All Services**

**Make sure you're setting it in the RIGHT service:**

1. **In Railway Dashboard:**
   - Look at all services in your project
   - Find the one that runs your **backend** (FastAPI)
   - That's where `OPENAI_API_KEY` must be set

2. **If you have multiple services:**
   - Backend service needs `OPENAI_API_KEY`
   - Frontend service does NOT need it

---

## 📋 **Quick Checklist**

- [ ] Variable name is exactly `OPENAI_API_KEY` (all uppercase, underscores)
- [ ] Variable value is your actual OpenAI key (starts with `sk-`)
- [ ] Variable is set in the **backend service** (not frontend, not project level)
- [ ] Variable appears in Railway Variables list
- [ ] Railway has redeployed after setting variable
- [ ] Check logs for diagnostic output
- [ ] Logs show `OPENAI_API_KEY: [your-key]` (not "NOT SET")

---

## 🎯 **Expected Log Output (After Fix)**

Once Railway passes the variable correctly:

```
🔍 ENVIRONMENT VARIABLES DIAGNOSTIC - ALL VARIABLES
🔍 Found OpenAI/API related variables:
  OPENAI_API_KEY: sk-proj-abc...xyz (length: 51)
🔍 CHECKING SPECIFIC VARIABLES:
  OPENAI_API_KEY: sk-proj-abc...xyz (length: 51)
✅ Found OPENAI_API_KEY via os.environ fallback (Railway compatibility)
✅ OpenAI API key is set
✅ ALL STARTUP VALIDATIONS PASSED
```

---

## 🚨 **If Still Not Working**

**If the diagnostic logs show "No OpenAI/API related variables found":**

1. **Railway is definitely not passing the variable**
2. **Try these steps:**
   - Delete the variable
   - Wait 1 minute
   - Re-add it (type the name, don't copy-paste)
   - Make sure it's in the **backend service**
   - Force redeploy
   - Check logs again

3. **If still not working:**
   - This might be a Railway bug
   - Try setting it via Railway CLI
   - Or contact Railway support

---

**The new diagnostic code will show EXACTLY what environment variables Railway is providing. Check the logs after the next deploy!** 🚀
