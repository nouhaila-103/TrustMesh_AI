import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="TrustMesh AI", page_icon="🛡️", layout="centered")
st.title("🛡️ TrustMesh AI")
st.caption("The AI Trust Layer for Secure Digital Services — GSMA MENA Ignite")

st.markdown("### Simulate a transaction")

SCENARIOS = {
    "Legitimate login": dict(phone_number="+99999991001", lat=25.227, lon=60.252),
    "Recent SIM swap (high risk)": dict(phone_number="+99999990001", lat=25.227, lon=60.252),
    "Impossible travel (location mismatch)": dict(phone_number="+99999991001", lat=48.8566, lon=2.3522),
}

scenario_name = st.selectbox("Demo scenario", list(SCENARIOS.keys()))
scenario = SCENARIOS[scenario_name]

col1, col2 = st.columns(2)
with col1:
    phone_number = st.text_input("Phone number (NaC simulator number)", scenario["phone_number"])
    transaction_type = st.selectbox("Transaction type", ["login", "payment", "identity_verification"])
with col2:
    lat = st.number_input("Claimed latitude", value=float(scenario["lat"]), format="%.4f")
    lon = st.number_input("Claimed longitude", value=float(scenario["lon"]), format="%.4f")

if st.button("Evaluate transaction", type="primary"):
    with st.spinner("Agent orchestrating CAMARA signals..."):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/evaluate-transaction",
                json={
                    "phone_number": phone_number,
                    "transaction_type": transaction_type,
                    "claimed_latitude": lat,
                    "claimed_longitude": lon,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            st.error(f"Could not reach backend: {e}")
            st.stop()

    decision = data["decision"]
    color = {"APPROVE": "green", "CHALLENGE": "orange", "BLOCK": "red"}[decision]

    st.markdown(f"## Decision: :{color}[{decision}]")
    st.metric("Trust score", f"{data['trust_score']:.0f} / 100")
    st.progress(int(data["trust_score"]) / 100)

    st.markdown("### Reasoning chain (audit log)")
    st.info(data["reasoning"])

    with st.expander("Raw CAMARA signals fetched by the agent"):
        st.json(data["signals"])

st.divider()
st.markdown("### Recent decisions")
try:
    history = requests.get(f"{BACKEND_URL}/decisions", timeout=10).json()
    if history:
        st.dataframe(
            [
                {
                    "time": h["created_at"],
                    "phone": h["phone_number"],
                    "type": h["transaction_type"],
                    "score": h["trust_score"],
                    "decision": h["decision"],
                }
                for h in history
            ],
            use_container_width=True,
        )
    else:
        st.caption("No decisions yet.")
except Exception:
    st.caption("Backend not reachable yet.")
