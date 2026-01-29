# Technical Documentation

## 3. LLM Prompt Design

### System Prompt
```
You are an expert procurement analyst specializing in supplier risk assessment.

CRITICAL RULES:
1. Use ONLY the data provided - do not invent information
2. Be specific - include actual numbers, percentages, and supplier names

OUTPUT FORMAT - Respond with valid JSON only:
{
    "category": "string",
    "overall_risk_level": "Low | Medium | High",
    "key_risks": ["2-5 risk statements"],
    "negotiation_levers": ["2-5 leverage points"],
    "recommended_actions_next_90_days": ["3-5 actions"],
    "confidence_score": "0.0 to 1.0"
}

RISK CRITERIA:
- HIGH: Single-source >40% spend OR contract ≤3 months OR delivery <80%
- MEDIUM: Contract ≤6 months OR delivery 80-90%
- LOW: Diversified suppliers with good performance
```

### User Prompt
```
Analyze supplier data for "{category}":
[Supplier JSON with spend percentages]

SUMMARY:
- Total Spend: ${total}
- Suppliers: {count}
- Single-Source: {count}

Generate insights JSON.
```

### How I Enforce Structured Output
- JSON schema explicitly defined in prompt.
- Respond ONLY with JSON instruction.
- Pydantic validates the response.
- Regex fallback extracts JSON if LLM adds extra text.

### How I Avoid Hallucination
- Use ONLY the data provided- direct instruction.
- Pre-calculate spend percentages before sen.ding to LLM.
- Low temperature (0.3) reduces randomness.
- Explicit thresholds for risk levels not subjective.

---

## 4. Error Handling

### Empty Supplier List
```python
# models.py
suppliers: List[Supplier] = Field(..., min_length=1)
# Returns 422: "ensure this value has at least 1 item"
```

### Missing/Invalid Fields
```python
# models.py - Pydantic validates automatically
annual_spend_usd: float = Field(..., gt=0)           # Must be positive
on_time_delivery_pct: float = Field(..., ge=0, le=100)  # 0-100 range
# Returns 422 with field-specific error
```

### LLM Returns Invalid JSON
```python
# llm_service.py - Try to extract JSON anyway
try:
    return json.loads(cleaned)
except json.JSONDecodeError:
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        return json.loads(match.group())
```

### LLM API Fails
```python
# main.py - Fallback to rule-based generator
except Exception as e:
    return FallbackInsightGenerator.generate(request)
```





## 6. Sample Output (From Assignment Dataset)

```json
{
  "category": "IT Hardware",
  "overall_risk_level": "High",
  "key_risks": [
    "Single-source dependency on TechSource Inc. ($4.2M, 46% of spend)",
    "GlobalComp Solutions contract expires in 3 months",
    "GlobalComp on-time delivery (85%) below standard"
  ],
  "negotiation_levers": [
    "Volume leverage with TechSource Inc. (46% spend)",
    "NextGen Systems strong performer (97% on-time)",
    "Multi-region supplier base for competitive bidding"
  ],
  "recommended_actions_next_90_days": [
    "Initiate contract renewal with GlobalComp Solutions",
    "Issue RFQ for backup supplier to reduce TechSource risk",
    "Begin TechSource renewal discussions (expires in 6 months)"
  ],
  "confidence_score": 0.95
}
```



---

## 7. Confidence Score Logic

**LLM responses:** LLM assigns 0.0-1.0 based on data clarity, then I add +0.2 (capped at 0.95)

**Fallback responses:** Fixed 0.65 (lower score indicates rule-based, less nuanced)

```python
# LLM path
response.confidence_score = min(0.95, response.confidence_score + 0.2)

# Fallback path
confidence_score=0.65
```

---

## 8. Design Decisions

**Why single POST endpoint?**
- Simple for procurement teams.
- JSON is standard for input/output.
- Fast response (<5s) for dashboards.

**How it would scale:**
- Multiple categories → Add `/batch` endpoint with async processing
- Larger supplier lists → Chunk into 10-15 suppliers per LLM call
- Real systems → REST connectors for SAP Ariba, Coupa, Oracle

---

## 9. Time Taken

| Task | Time |
|------|------|
| FastAPI setup + POST endpoint | 20-25 minutes |
| Pydantic models (input/output) | 15-20 minutes |
| **Total for (1) and (2)** | **~45 minutes** |
