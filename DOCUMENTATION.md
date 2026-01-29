# Technical Documentation

## 3. LLM Prompt Design

### The Exact Prompt Used

**System Prompt:**
```
You are an expert procurement analyst specializing in supplier risk assessment.

CRITICAL RULES:
1. Use ONLY the data provided - do not invent information
2. Be specific - include actual numbers, percentages, and supplier names
3. Focus on actionable insights

OUTPUT FORMAT - Respond with valid JSON only:
{
    "category": "string",
    "overall_risk_level": "Low | Medium | High",
    "key_risks": ["array of 2-5 risk statements"],
    "negotiation_levers": ["array of 2-5 leverage points"],
    "recommended_actions_next_90_days": ["array of 3-5 actions"],
    "confidence_score": "number 0.0 to 1.0"
}

RISK CRITERIA:
- HIGH: Single-source >40% spend OR contract expiring ≤3 months OR delivery <80%
- MEDIUM: Contract expiring ≤6 months OR delivery 80-90%
- LOW: Diversified suppliers with good performance

Respond ONLY with JSON, no markdown or extra text.
```

**User Prompt (Dynamic):**
```
Analyze supplier data for "{category}":

[Supplier data as JSON with pre-calculated spend percentages]

SUMMARY:
- Total Spend: ${total}
- Suppliers: {count}
- Regions: {list}
- Single-Source: {count}

Generate insights JSON.
```

### How Structured Output is Enforced

1. **Explicit JSON Schema**: The exact output structure is defined in the prompt
2. **Field Constraints**: Enum values specified ("Low | Medium | High")
3. **No Markdown Instruction**: "Respond ONLY with JSON, no markdown"
4. **JSON Parsing with Fallback**: Code strips markdown backticks if present
5. **Pydantic Validation**: Response validated against `InsightResponse` model

### How Hallucination is Avoided

1. **Data Grounding**: "Use ONLY the data provided - do not invent information"
2. **Pre-computed Metrics**: Spend percentages calculated before sending to LLM
3. **Specificity Requirement**: "Include actual numbers, percentages, and supplier names"
4. **Explicit Risk Criteria**: Defined thresholds (>40%, ≤3 months, <80%)
5. **Low Temperature (0.3)**: Reduces creative/random outputs

---

## 4. Error Handling and Guardrails

### Empty Supplier List
```python
# In models.py - Pydantic validation
suppliers: List[Supplier] = Field(..., min_length=1)

# Returns 422 Unprocessable Entity with message:
# "ensure this value has at least 1 item"
```

### Missing or Malformed Fields
```python
# Pydantic automatically validates all fields
class Supplier(BaseModel):
    supplier_name: str = Field(..., min_length=1)      # Required, non-empty
    annual_spend_usd: float = Field(..., gt=0)          # Required, positive
    on_time_delivery_pct: float = Field(..., ge=0, le=100)  # 0-100 range
    
# Invalid data returns 422 with detailed field errors
```

### LLM Returns Invalid JSON
```python
def parse_response(text: str) -> dict:
    cleaned = text.strip()
    
    # Strip markdown code blocks if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract JSON from mixed content
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            return json.loads(match.group())
        raise ValueError("Failed to parse JSON")
```

### LLM API Failure
```python
# In main.py - Graceful fallback
try:
    if llm_service:
        response = await llm_service.generate_insights(request)
    else:
        response = FallbackInsightGenerator.generate(request)
except Exception as e:
    logger.error(f"LLM Error: {e}")
    # Fall back to rule-based generator
    response = FallbackInsightGenerator.generate(request)
```

---

## 7. Confidence Score Logic

### How is `confidence_score` Calculated?

**For LLM-generated responses:**
- The LLM assigns a score (0.0-1.0) based on data clarity
- Score is boosted by +0.2 (capped at 0.95) for AI-generated responses
- Final score reflects analysis confidence

**For Fallback (rule-based) responses:**
- Fixed score of 0.65 (lower than LLM)
- Indicates deterministic but less nuanced analysis

**Factors Influencing Score:**

| Factor | Impact |
|--------|--------|
| Clear risk signals (single-source, expiring contracts) | Higher score |
| Complete supplier data | Higher score |
| Multiple suppliers (more data) | Higher score |
| Ambiguous patterns | Lower score |
| Missing fields | Lower score |

**Code Implementation:**
```python
# LLM response processing
response = validate_response(data, request)
response.confidence_score = min(0.95, response.confidence_score + 0.2)

# Fallback generator
return InsightResponse(
    ...
    confidence_score=0.65  # Fixed lower score
)
```

---

## 8. Design Decisions

### Why This Endpoint Structure?

1. **Single POST endpoint**: Procurement executives need quick, simple access
2. **JSON input/output**: Standard for modern APIs, easy integration
3. **Category + Suppliers design**: Mirrors how procurement data is organized
4. **Synchronous response**: Dashboard latency requirements (<5s)

### How This Would Scale

**Multiple Categories:**
```python
# Add batch endpoint
@app.post("/generate-insights/batch")
async def batch_insights(requests: List[InsightRequest]):
    return await asyncio.gather(*[
        generate_insights(req) for req in requests
    ])
```

**Larger Supplier Lists:**
- Chunk suppliers into groups of 10-15 per LLM call
- Aggregate results across chunks
- Implement pagination for very large lists

**Real Procurement Systems:**

| Integration | Approach |
|-------------|----------|
| SAP Ariba | REST connector, OAuth2 auth |
| Coupa | Webhook triggers on data changes |
| Oracle | Database sync, scheduled jobs |
| Workday | API gateway integration |

**Additional Scaling Considerations:**
- Redis caching for repeated queries
- Message queue (RabbitMQ/Kafka) for async processing
- Horizontal scaling with Kubernetes
- Multi-region deployment for global teams

---

## Sample JSON Response (From Provided Dataset)

```json
{
  "category": "IT Hardware",
  "overall_risk_level": "High",
  "key_risks": [
    "Single-source dependency on TechSource Inc. ($4.2M, 46% of total spend) creates supply chain vulnerability",
    "Urgent: GlobalComp Solutions contract expires in 3 months requiring immediate action",
    "Performance risk: GlobalComp Solutions on-time delivery (85%) below industry standard"
  ],
  "negotiation_levers": [
    "Volume leverage with TechSource Inc. (46% of category spend) for pricing negotiations",
    "Top performer NextGen Systems (97% on-time) - potential for volume expansion",
    "Multi-region supplier base enables competitive bidding across geographies"
  ],
  "recommended_actions_next_90_days": [
    "Week 1-2: Initiate contract renewal negotiations with GlobalComp Solutions",
    "Week 3-6: Issue RFQ for backup supplier to reduce TechSource single-source risk",
    "Week 4-8: Conduct performance review with GlobalComp, set 90% OTD improvement target",
    "Month 3: Begin TechSource contract renewal discussions (expires in 6 months)"
  ],
  "confidence_score": 0.87
}
```
