# Supplier Sourcing Insights API

FastAPI app that generates procurement insights using LLM.

**Live Demo:** https://coding-assignment-supplierinsightsapi-production.up.railway.app/docs

**LLM Used:** Groq (llama-3.3-70b) - chose this because it's free with generous rate limits, making it ideal for development and demos.

**Frontend:** I also built a simple Streamlit frontend for easier interaction. Run locally with `streamlit run frontend.py` → http://localhost:8501

---


## How to Run Locally

```bash
# Setup
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Add API key (free at https://console.groq.com/keys)
echo "GROQ_API_KEY=your_key_here" > .env

# Run
uvicorn app.main:app --reload
```

Open: http://127.0.0.1:8000/docs

---

## Example Request

```bash
curl -X POST "http://127.0.0.1:8000/generate-insights" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "IT Hardware",
    "suppliers": [
      {
        "supplier_name": "TechSource Inc.",
        "annual_spend_usd": 4200000,
        "on_time_delivery_pct": 92,
        "contract_expiry_months": 6,
        "single_source_dependency": true,
        "region": "North America"
      }
    ]
  }'
```

## Example Response

```json
{
  "category": "IT Hardware",
  "overall_risk_level": "High",
  "key_risks": [
    "Single-source dependency on TechSource Inc. ($4.2M, 100% of spend)"
  ],
  "negotiation_levers": [
    "Volume leverage with TechSource Inc."
  ],
  "recommended_actions_next_90_days": [
    "Develop backup supplier to reduce single-source risk"
  ],
  "confidence_score": 0.85
}
```

---

## Assumptions

- All spend values in USD.
- On-time delivery % is the primary performance metric.
- Risk thresholds: High (>40% single-source, contract ≤3mo, delivery <80%), Medium (contract ≤6mo, delivery 80-90%), Low (diversified, good performance).
- 'Next 90 days' is the planning window.

---

## Production Improvements

- **Better LLM Models** - Switch to OpenAI GPT-4 or Claude for more nuanced analysis (paid but higher quality).
- **Authentication** - Add JWT/API keys.
- **Rate Limiting** - Per-client limits.
- **Caching** - Redis for repeated queries.
- **Database** - Store historical analyses for trend tracking.
- **Monitoring** - Prometheus metrics, alerting.
- **Scaling** - Kubernetes with auto-scaling.
- **Multiple LLMs** - Fallback to OpenAI/Claude if Groq fails.

---
