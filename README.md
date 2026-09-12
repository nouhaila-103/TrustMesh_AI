# TrustMesh AI — prototype

AI trust orchestration layer built on Nokia Network-as-Code (GSMA CAMARA APIs) + LangGraph.

Tested end-to-end and working (verified in a degraded/no-token mode; plug in a real `NAC_TOKEN` for live signals).

## 1. Get Nokia Network-as-Code access (do this first, ~5 min)

1. Go to https://dashboard.networkascode.nokia.io/ and self-register (no special approval needed).
2. Create an application, subscribe it to: **SIM Swap**, **Device Status**, **Location Verification**.
3. Copy your application key.
4. Use the NaC **simulator phone numbers** (documented in the portal, e.g. `+99999991000`) so responses are deterministic for your demo — no real SIM needed.

## 2. Run the backend

```bash
cd backend
cp .env.example .env        # paste your NAC_TOKEN in here
pip install -r requirements.txt --break-system-packages
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Check it's alive: `curl http://localhost:8000/health`

Interactive API docs: http://localhost:8000/docs

## 3. Run the frontend (demo UI)

```bash
cd frontend
pip install -r requirements.txt --break-system-packages
streamlit run app.py
```

Opens at http://localhost:8501 — pick a scenario, hit "Evaluate transaction", see the trust score,
decision (APPROVE/CHALLENGE/BLOCK), and full reasoning chain.

## 4. Optional: LLM-generated reasoning

By default the reasoning chain is a deterministic rule-based sentence (safe for live demos —
never crashes, no API cost). To use an LLM instead, set `OPENAI_API_KEY` in `backend/.env`.

## 5. Deploy (mandatory for hackathon submission)

Fastest path — single VM, no container orchestration needed:

1. Spin up one Ubuntu EC2 instance (or any VPS).
2. `git clone` this repo, follow steps 2 and 3 above on the box.
3. Run both processes under `tmux` or `systemd`:
   ```bash
   tmux new -s backend -d "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000"
   tmux new -s frontend -d "cd frontend && BACKEND_URL=http://localhost:8000 streamlit run app.py --server.port 8501 --server.address 0.0.0.0"
   ```
4. Open the security group / firewall for ports 8000 and 8501.
5. Share the public IP:8501 link (frontend) in your submission; keep :8000 open so the frontend can reach it.

If your later architecture needs gRPC or something Vercel/Railway can't serve, this single-EC2
approach is the right call for a demo — don't over-engineer the deployment before the deadline.

## Architecture

```
Streamlit UI  --HTTP-->  FastAPI  --invokes-->  LangGraph agent
                                                    |
                                    +---------------+---------------+
                                    |               |                |
                              SIM Swap check   Reachability    Location verify
                                    |               |                |
                                    +-------- Nokia Network-as-Code -+
                                                    |
                                          fuse signals -> trust score
                                                    |
                                          decision + reasoning chain
                                                    |
                                          SQLite (audit log)
```

## What's mocked vs real

- **Real**: SIM Swap, Device Status (reachability), Location Verification — all live calls to
  Nokia Network-as-Code (CAMARA-compliant), using simulator numbers for deterministic demo data.
- **Not implemented** (cut for time): Number Verification, which requires a 3-legged OAuth
  consent flow with the end-user's browser/device — out of scope for a backend-only demo. Mention
  this honestly in the pitch: the architecture supports adding it as a 4th signal.
