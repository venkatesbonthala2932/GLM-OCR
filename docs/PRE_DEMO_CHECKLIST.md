# Pre-demo checklist

Run through this **30 minutes before** your presentation. Tick every box.
If any box fails, fix it before the demo — do not present with known
issues.

---

## 30 minutes before

### Hardware

- [ ] Laptop fully charged or plugged in
- [ ] Wifi connected (only needed if you want to show the GitHub repo)
- [ ] Close all unrelated applications — leave only Terminal, VS Code,
      browser, and Preview open
- [ ] Display set to a font size that's readable from across the room
      (System Settings → Displays → Larger Text)

### Environment

```bash
# In your terminal, cd into the project
cd /Users/venkateshbonthala/GLM-OCR

# Activate the venv
source .venv/bin/activate
```

- [ ] Prompt now shows `(.venv)` at the front
- [ ] `python --version` reports 3.10 or higher

---

## 20 minutes before

### Start the webapp once

```bash
python webapp.py
```

- [ ] Output ends with `[startup] model ready in NN.Ns`
- [ ] Output ends with `Uvicorn running on http://0.0.0.0:8000`
- [ ] No tracebacks or red error text visible

### Sanity-test the webapp

Open http://localhost:8000 in your browser:

- [ ] The page loads — title says "GLM-OCR"
- [ ] Drop zone and "Run OCR" button are visible

Drag `examples/source/code.png` into the drop zone:

- [ ] File appears in the list with size in KB
- [ ] Click "Run OCR"
- [ ] Within ~25 seconds, recognised code text appears
- [ ] Click "Reset" — list and output clear

If any of the above fails, **do not present** — see Troubleshooting
below.

---

## 10 minutes before

### Tabs and files ready

Open these in your browser in this order (so Cmd+1, Cmd+2, Cmd+3 are
predictable during the demo):

- [ ] Tab 1: http://localhost:8000
- [ ] Tab 2: https://github.com/venkatesbonthala2932/GLM-OCR
- [ ] Tab 3: file://...docs/PROJECT_REPORT.pdf (open in Preview is also fine)

On your Desktop, have ready:

- [ ] One image you want to OCR live (your own, or a copy of
      `examples/source/code.png`)
- [ ] One PDF you want to OCR live (your own, or a copy of
      `examples/source/GLM-4.5V.pdf`)

### Notes ready

- [ ] `DEMO_GUIDE.md` open in VS Code on a second monitor, OR printed
- [ ] You have read the Q&A section at least once today
- [ ] You can name **three** limitations of the system off the top of
      your head (the Indian-language gap, no authentication, ~45 s per
      image)

---

## 2 minutes before

- [ ] Webapp terminal still shows the server running (no `Ctrl+C`
      accidentally)
- [ ] Browser tab 1 (the webapp) refreshes cleanly
- [ ] You've taken a sip of water

---

## During the demo

Keep your eye on:

1. The browser **status text** — it tells you whether OCR is running
   or completed. If you see "Error:" mention it calmly, switch to a
   different sample.
2. The terminal — if a Python traceback appears, **do not panic**.
   Open the PDF report tab and continue talking about the architecture
   while you collect yourself.

---

## After the demo

- [ ] Press `Ctrl+C` in the terminal to stop the webapp cleanly
- [ ] Note any questions you couldn't answer
- [ ] Send the follow-up email (repo link + PDF report attached) within
      24 hours

---

## Troubleshooting (only if pre-demo tests fail)

### "Form data requires python-multipart"

```bash
pip install python-multipart
```

### Webapp starts but `localhost:8000` shows nothing

Wait 30 more seconds — the first request also triggers some lazy
imports. If still empty, check the terminal for errors.

### Model load takes more than 60 seconds

You're on a slow connection downloading the model for the first time.
This won't happen if the cache at `~/.cache/huggingface/hub/` already
has `models--zai-org--GLM-OCR` (2.5 GB). Verify with:

```bash
du -sh ~/.cache/huggingface/hub/models--zai-org--GLM-OCR
```

### "ModuleNotFoundError: No module named 'fastapi'"

Your venv is not activated. Run `source .venv/bin/activate` and try
again.

### Browser shows "This site can't be reached"

The webapp isn't running. Switch to the terminal — it should show the
uvicorn output. If not, restart it: `python webapp.py`.

### OCR returns blank or random text

You uploaded a script the model wasn't trained on (Indian language,
Arabic, etc.). This is a known limitation — mention it openly and switch
to an English/Chinese sample.

---

## One-line summary you should be able to recite

> "Local GLM-OCR deployment, image and PDF uploads through a browser
> interface, fully offline, zero recurring cost, validated across eight
> document categories, with known limitations on Indian-language scripts
> documented as the next iteration."

If you can say that sentence cleanly, you're ready.
