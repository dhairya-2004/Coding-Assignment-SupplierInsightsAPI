# Supplier Sourcing Insights API

A FastAPI application that generates structured procurement insights using Google Gemini LLM.

---

## 1. How to Run the API Locally

### Prerequisites
- Python 3.10+
- Google Gemini API key (free at https://aistudio.google.com/app/apikey)

### Setup
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "GOOGLE_API_KEY=your_api_key_here" > .env

# Run server
uvicorn app.main:app --reload
```

### Access
- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

---

## 2. How to Call the Endpoint

### Example Request
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
      },
      {
        "supplier_name": "GlobalComp Solutions",
        "annual_spend_usd": 3100000,
        "on_time_delivery_pct": 85,
        "contract_expiry_months": 3,
        "single_source_dependency": false,
        "region": "Asia"
      },
      {
        "supplier_name": "NextGen Systems",
        "annual_spend_usd": 1800000,
        "on_time_delivery_pct": 97,
        "contract_expiry_months": 12,
        "single_source_dependency": false,
        "region": "Europe"
      }
    ]
  }'
```

### Example Response
```json
{
  "category": "IT Hardware",
  "overall_risk_level": "High",
  "key_risks": [
    "Single-source dependency on TechSource Inc. ($4.2M, 46% of spend)",
    "Urgent: GlobalComp Solutions contract expires in 3 months",
    "Low delivery performance: GlobalComp Solutions at 85%"
  ],
  "negotiation_levers": [
    "Volume leverage with TechSource Inc. (46% of category spend)",
    "Top performer: NextGen Systems (97% on-time delivery)",
    "Volume leverage with GlobalComp Solutions (34% spend)"
  ],
  "recommended_actions_next_90_days": [
    "Immediate: Initiate contract renewal with GlobalComp Solutions",
    "Develop backup supplier for TechSource Inc. single-source risk",
    "Begin contract renewal discussions with TechSource Inc. (expires in 6 months)"
  ],
  "confidence_score": 0.87
}
```

---

## 3. Assumptions

1. **Data Quality**: Input supplier data is accurate and complete
2. **Currency**: All spend values are in USD
3. **Delivery Metric**: On-time delivery percentage (0-100) is the primary performance KPI
4. **Time Horizon**: "Next 90 days" is the actionable planning window
5. **Risk Thresholds**:
   - High risk: >40% spend with single source, or contract ≤3 months, or delivery <80%
   - Medium risk: Contract ≤6 months, or delivery 80-90%
   - Low risk: Diversified suppliers with good performance

---

## 4. Production Improvements

| Area | Current | Production Enhancement |
|------|---------|----------------------|
| **Authentication** | None | Add JWT/API key authentication |
| **Rate Limiting** | None | Implement per-client rate limits |
| **Caching** | None | Cache identical requests (Redis) |
| **Database** | None | Store historical analyses for trends |
| **Monitoring** | Basic logging | Add Prometheus metrics, alerts |
| **Scaling** | Single instance | Kubernetes with auto-scaling |
| **LLM Fallback** | Rule-based | Multiple LLM providers (OpenAI, Claude) |
| **Async Processing** | Sync | Queue long-running analyses (Celery) |
| **Testing** | Manual | Automated CI/CD pipeline |
| **Security** | Basic | Input sanitization, HTTPS, audit logs |

---

## 5. Project Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic models
│   └── llm_service.py    # Gemini LLM integration
├── .env                  # API keys (not in git)
├── requirements.txt
└── README.md
```

---

## 6. Time Taken

| Task | Time |
|------|------|
| FastAPI setup + endpoint | 15 min |
| Pydantic models | 10 min |
| LLM integration + prompts | 20 min |
| Error handling | 10 min |
| Testing & debugging | 15 min |
| **Total (Points 1 & 2)** | **~70 minutes** |

---

## Author
Dhairya - M.S. Computer Science, Northeastern University