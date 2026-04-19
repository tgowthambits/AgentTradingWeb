# 🔧 Real-Time Backtest Debug Guide

## 🐛 PROBLEM
Backtest running but frontend not updating in real-time.

## 🔍 DEBUG STEPS

### Step 1: Restart UI Server with Debug Logging

Stop the current UI server (Ctrl+C) and restart it:

```bash
cd /home/sham/Desktop/MARKOV_MARKET/trading_system/ui/backend
python main.py
```

**Look for:**
```
[Backend] Starting backtest broadcast task...
```

This confirms the broadcast task is running.

---

### Step 2: Open Debug Console

**In your browser, open:**
```
http://localhost:8000/backtest-debug.html
```

This is a special debug page that shows:
- ✅ WebSocket connection status
- 📨 All messages received
- 📊 Backtest updates in real-time
- Full message data in console (F12)

**You should see:**
```
Status: Connected
✅ WebSocket Connected!
```

---

### Step 3: Run Backtest with Debug Output

```bash
cd /home/sham/Desktop/MARKOV_MARKET
python trading_system/run_live_bot.py
```

**Look for these messages:**

1. **On startup:**
   ```
   ✅ DataBridge connected for real-time updates
   ```

2. **When backtest starts:**
   ```
   🌐 Real-time UI updates enabled (Capital: ₹20,000, Iterations: 100)
   ```

3. **During backtest:**
   - Terminal should show: `[DataBridge] Updating backtest - iteration: X`
   - UI server should show: `[Backend] Broadcasting backtest update - iteration: X`

---

### Step 4: Check Debug Console

In the debug page (http://localhost:8000/backtest-debug.html), you should see:

```
📊 BACKTEST UPDATE: Iteration 1, Progress: 1.0%, Capital: ₹19,995
📊 BACKTEST UPDATE: Iteration 2, Progress: 2.0%, Capital: ₹19,690
📊 BACKTEST UPDATE: Iteration 3, Progress: 3.0%, Capital: ₹19,390
...
```

Messages should appear every ~500ms while backtest is running.

---

## 🎯 WHAT TO CHECK

### Check 1: Is data_bridge available?

Run this command:
```bash
cd /home/sham/Desktop/MARKOV_MARKET
python -c "from trading_system.ui.backend.data_bridge import data_bridge; print('✅ data_bridge OK')"
```

Should show: `✅ data_bridge OK`

---

### Check 2: Is WebSocket connecting?

**Browser Console (F12):**
```javascript
// Should see:
WebSocket state: 1  // 1 = OPEN (good!)
```

If state is not 1:
- 0 = CONNECTING
- 2 = CLOSING
- 3 = CLOSED

---

### Check 3: Is UI server running?

```bash
ps aux | grep main.py
```

Should show a running `python main.py` process.

---

### Check 4: Are ports correct?

**UI Server:** Port 8000
**WebSocket:** ws://localhost:8000/ws

Check in browser console:
```javascript
// Should connect to:
ws://localhost:8000/ws
```

---

## 🔧 COMMON ISSUES & FIXES

### Issue 1: "DataBridge not available"

**Symptom:** Backtest shows warning about data_bridge

**Solution:**
```bash
# The import should work, try:
cd /home/sham/Desktop/MARKOV_MARKET
python -c "from trading_system.ui.backend.data_bridge import data_bridge; print(data_bridge)"
```

If this fails, the file might have syntax errors.

---

### Issue 2: WebSocket won't connect

**Symptom:** Debug page shows "Status: Disconnected"

**Solution:**
1. Check UI server is running
2. Restart UI server
3. Check browser console for errors (F12)
4. Try different browser

---

### Issue 3: No broadcast messages

**Symptom:** WebSocket connected but no backtest messages

**Solution:**
1. Check UI server logs - should see `[Backend] Broadcasting backtest update`
2. Check if `data_bridge.backtest_active` is True:
   ```bash
   curl http://localhost:8000/api/backtest/state
   ```
3. Restart UI server to reload code changes

---

### Issue 4: Old data showing

**Symptom:** UI shows old backtest, not current one

**Solution:**
1. Hard refresh browser: Ctrl+Shift+R
2. Check data_bridge state:
   ```bash
   curl http://localhost:8000/api/backtest/state
   ```
3. Clear browser cache

---

## 📊 TEST SEQUENCE

### Complete Test:

1. **Terminal 1** - Start UI server:
   ```bash
   cd trading_system/ui/backend
   python main.py
   ```
   ✅ Look for: "Starting backtest broadcast task..."

2. **Browser Tab 1** - Open debug console:
   ```
   http://localhost:8000/backtest-debug.html
   ```
   ✅ Should show: "Status: Connected"

3. **Terminal 2** - Run backtest:
   ```bash
   python trading_system/run_live_bot.py
   ```
   ✅ Look for: "Real-time UI updates enabled"

4. **Browser Tab 1** - Watch debug messages:
   ✅ Should see: "BACKTEST UPDATE" messages every 500ms

5. **Browser Tab 2** - Open actual backtest UI:
   ```
   http://localhost:8000/backtest
   ```
   ✅ Should see: Summary updating, trades appearing

---

## 🎯 EXPECTED TERMINAL OUTPUT

### UI Server Terminal:
```
✅ API Ready!
📊 Dashboard: http://localhost:8000
🔌 WebSocket: ws://localhost:8000/ws
[Backend] Starting backtest broadcast task...
```

**When backtest runs:**
```
[Backend] Broadcasting backtest update - iteration: 1
[Backend] Broadcasting backtest update - iteration: 2
[Backend] Broadcasting backtest update - iteration: 3
...
```

### Backtest Terminal:
```
✅ DataBridge connected for real-time updates
🔄 Starting Backtest...
🌐 Real-time UI updates enabled (Capital: ₹20,000, Iterations: 100)
```

**During backtest:**
```
[DataBridge] Updating backtest - iteration: 1, has_trade: True
[DataBridge] Updating backtest - iteration: 2, has_trade: True
...
```

---

## 🚀 QUICK FIX CHECKLIST

If real-time updates not working:

- [ ] UI server restarted (Ctrl+C, then `python main.py`)
- [ ] Debug page shows "Connected" status
- [ ] Backtest shows "Real-time UI updates enabled"
- [ ] UI server logs show "Broadcasting backtest update"
- [ ] Backtest terminal shows "[DataBridge] Updating backtest"
- [ ] Browser hard refreshed (Ctrl+Shift+R)
- [ ] No errors in browser console (F12)
- [ ] Correct URL: http://localhost:8000/backtest

---

## 💡 ADDITIONAL DEBUG COMMANDS

### Check backtest state via API:
```bash
curl http://localhost:8000/api/backtest/state
```

### Check WebSocket from command line:
```bash
# Install wscat if needed: npm install -g wscat
wscat -c ws://localhost:8000/ws
```

### Test data_bridge directly:
```python
from trading_system.ui.backend.data_bridge import data_bridge
data_bridge.start_backtest(20000, 100)
data_bridge.update_backtest(iteration=5, summary={'total_pnl': -150})
print(data_bridge.get_backtest_state())
```

---

## ✅ SUCCESS INDICATORS

You'll know it's working when:

1. **UI Server logs** show broadcast messages
2. **Debug page** shows live backtest updates
3. **Main backtest page** updates automatically
4. **Browser title** shows progress percentage
5. **Trades table** gets new rows without refresh
6. **Summary numbers** update every 500ms

---

## 📞 STILL NOT WORKING?

### Collect this info:

1. **UI Server logs** (last 20 lines)
2. **Backtest terminal output** (especially startup messages)
3. **Browser console** (F12, any errors?)
4. **Debug page messages** (what's appearing?)
5. **API state check:**
   ```bash
   curl http://localhost:8000/api/backtest/state
   ```

---

**Use the debug console at http://localhost:8000/backtest-debug.html to see exactly what's happening! 🔍**

