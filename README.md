# Side Hustle Idea Generator

> Make money from your skills

---

## ⚡ Get running in 5 minutes

### Step 1 — Get a free Groq API key
1. Go to **https://console.groq.com**
2. Sign up (free, no credit card)
3. Click **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

### Step 2 — Set up the project

Open your terminal in this folder and run these commands **one at a time**:

```bash
# Create a virtual environment (keeps things tidy)
python -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3 — Add your API key

1. Find the file called `.env.example` in this folder
2. **Rename it** to `.env`  (remove the `.example` part)
3. Open `.env` in any text editor
4. Replace `your_groq_key_here` with the key you copied in Step 1

It should look like this:
```
GROQ_API_KEY=gsk_abc123...your_actual_key
```

### Step 4 — Run it

```bash
uvicorn main:app --reload
```

Then open your browser and go to: **http://localhost:8000**

---

## Stopping the app

Press `Ctrl + C` in your terminal.

## Starting it again later

```bash
# Activate your virtual environment first
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows

# Then run
uvicorn main:app --reload
```

---

Built with [Launchpad](https://launchpad.app) · Powered by [Groq](https://console.groq.com)
