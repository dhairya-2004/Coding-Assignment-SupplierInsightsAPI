# LLM Prompt Design Documentation

## Overview

This document details the prompt engineering strategy used in the Supplier Sourcing Insights API to generate high-quality, structured procurement insights.

## Design Philosophy

### 1. Structured Output Enforcement

The LLM must return a specific JSON schema. We achieve this through multiple layers:

#### Layer 1: Schema Specification in System Prompt

```
OUTPUT FORMAT:
You must respond with a valid JSON object matching this exact schema:
{
    "category": "string - the category name from input",
    "overall_risk_level": "Low | Medium | High",
    "key_risks": ["array of 2-5 specific risk statements"],
    "negotiation_levers": ["array of 2-5 strategic leverage points"],
    "recommended_actions_next_90_days": ["array of 3-5 prioritized actions"],
    "confidence_score": "number between 0.0 and 1.0"
}
```

**Why this works**: Explicit schema with field descriptions leaves no ambiguity.

#### Layer 2: OpenAI JSON Mode

```python
response_format: {"type": "json_object"}
```

**Why this works**: API-level enforcement guarantees valid JSON syntax.

#### Layer 3: Pydantic Post-Validation

```python
response = InsightResponse(**parsed_data)
```

**Why this works**: Catches semantic errors (wrong types, missing fields, out-of-range values).

### 2. Anti-Hallucination Strategy

Hallucination is prevented through data grounding:

#### Technique 1: Explicit Grounding Instructions

```
CRITICAL RULES:
1. Use ONLY the data provided - do not invent or assume any information
2. All insights must be directly traceable to the input data
3. Be specific - include actual numbers, percentages, and supplier names
```

#### Technique 2: Pre-computed Context

Before calling the LLM, we compute and include:
- Total spend across suppliers
- Spend share percentage per supplier
- Number of single-source dependencies
- Regional distribution

This gives the LLM concrete numbers to reference rather than requiring it to calculate.

#### Technique 3: Specificity Requirements

```
Focus on actionable intelligence for procurement executives
Reference specific suppliers and numbers in your insights
```

Forcing specific references makes hallucination harder.

#### Technique 4: Temperature Control

```python
temperature=0.3  # Lower = more deterministic
```

Low temperature reduces creative variation that could introduce fabricated details.

### 3. Risk Level Determination

Clear criteria ensure consistent classification:

```
RISK LEVEL CRITERIA:
- HIGH: Single-source dependency on major supplier (>40% spend) OR 
        contract expiring within 3 months OR on-time delivery <80%
- MEDIUM: Contract expiring within 6 months OR on-time delivery 80-90% 
          OR concentration risk
- LOW: Diversified supplier base with good performance and stable contracts
```

**Why explicit thresholds**: Prevents subjective interpretation and ensures reproducibility.

## Full System Prompt

```
You are an expert procurement analyst specializing in supplier risk assessment 
and strategic sourcing.

Your task is to analyze supplier data and generate structured insights for 
executive decision-making.

CRITICAL RULES:
1. Use ONLY the data provided - do not invent or assume any information
2. All insights must be directly traceable to the input data
3. Be specific - include actual numbers, percentages, and supplier names
4. Focus on actionable intelligence for procurement executives

OUTPUT FORMAT:
You must respond with a valid JSON object matching this exact schema:
{
    "category": "string - the category name from input",
    "overall_risk_level": "Low | Medium | High",
    "key_risks": ["array of 2-5 specific risk statements"],
    "negotiation_levers": ["array of 2-5 strategic leverage points"],
    "recommended_actions_next_90_days": ["array of 3-5 prioritized actions"],
    "confidence_score": "number between 0.0 and 1.0"
}

RISK LEVEL CRITERIA:
- HIGH: Single-source dependency on major supplier (>40% spend) OR 
        contract expiring within 3 months OR on-time delivery <80%
- MEDIUM: Contract expiring within 6 months OR on-time delivery 80-90% 
          OR concentration risk
- LOW: Diversified supplier base with good performance and stable contracts

CONFIDENCE SCORE CALCULATION:
Base confidence on data quality and completeness:
- Start at 0.7 for basic analysis
- +0.1 if data has clear patterns
- +0.1 if recommendations are strongly supported by data
- -0.1 if data has gaps or conflicts
- -0.1 if analysis requires assumptions beyond data

Respond ONLY with the JSON object, no additional text or markdown formatting.
```

## Full User Prompt Template

```
Analyze the following supplier data for the "{category}" category:

SUPPLIER DATA:
{json_formatted_supplier_data}

SUMMARY METRICS:
- Total Annual Spend: ${total_spend}
- Number of Suppliers: {supplier_count}
- Regions Covered: {regions}
- Single-Source Dependencies: {single_source_count}

Generate the structured insights JSON based on this data. Remember to:
1. Reference specific suppliers and numbers in your insights
2. Prioritize immediate risks (contracts expiring soon, delivery issues)
3. Identify negotiation opportunities based on performance data
4. Provide actionable 90-day recommendations
```

## Example Prompt Instance

For the provided IT Hardware dataset:

```
Analyze the following supplier data for the "IT Hardware" category:

SUPPLIER DATA:
[
  {
    "supplier_name": "TechSource Inc.",
    "annual_spend_usd": 4200000,
    "spend_share_pct": 46.2,
    "on_time_delivery_pct": 92,
    "contract_expiry_months": 6,
    "single_source_dependency": true,
    "region": "North America"
  },
  {
    "supplier_name": "GlobalComp Solutions",
    "annual_spend_usd": 3100000,
    "spend_share_pct": 34.1,
    "on_time_delivery_pct": 85,
    "contract_expiry_months": 3,
    "single_source_dependency": false,
    "region": "Asia"
  },
  {
    "supplier_name": "NextGen Systems",
    "annual_spend_usd": 1800000,
    "spend_share_pct": 19.8,
    "on_time_delivery_pct": 97,
    "contract_expiry_months": 12,
    "single_source_dependency": false,
    "region": "Europe"
  }
]

SUMMARY METRICS:
- Total Annual Spend: $9,100,000
- Number of Suppliers: 3
- Regions Covered: North America, Asia, Europe
- Single-Source Dependencies: 1

Generate the structured insights JSON based on this data.
```

## Error Recovery

### Invalid JSON from LLM

```python
def _parse_llm_response(self, response_text: str) -> dict:
    # 1. Strip markdown code blocks
    cleaned = re.sub(r'^```(?:json)?\s*', '', response_text.strip())
    cleaned = re.sub(r'\s*```$', '', cleaned)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # 2. Extract JSON from mixed content
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError("Could not parse JSON")
```

### Missing/Invalid Fields

```python
def _validate_and_normalize(self, data: dict, request: InsightRequest):
    # Normalize risk level with fallback
    risk_level = risk_level_map.get(
        data.get("overall_risk_level", "Medium").lower(), 
        RiskLevel.MEDIUM
    )
    
    # Bound confidence score
    confidence = max(0.0, min(1.0, float(data.get("confidence_score", 0.7))))
    
    # Ensure non-empty lists
    key_risks = data.get("key_risks", [])
    if not key_risks:
        key_risks = [f"Data quality insufficient for {request.category} assessment"]
```

## Prompt Evolution Notes

### Version 1 (Initial)
- Simple instruction to analyze suppliers
- Problem: Inconsistent output format, narrative paragraphs

### Version 2 (Schema Added)
- Added explicit JSON schema
- Problem: Risk levels inconsistent ("high" vs "High" vs "HIGH")

### Version 3 (Criteria Added)
- Added explicit risk level criteria with thresholds
- Added confidence scoring guidance
- Problem: Sometimes included markdown formatting

### Version 4 (Final)
- Added "Respond ONLY with JSON, no markdown"
- Added API-level JSON mode
- Added post-processing normalization
- Result: Consistent, reliable structured output

## Testing Prompt Effectiveness

The test suite validates prompt effectiveness:

```python
def test_detects_single_source_risk(self):
    """Verify LLM identifies single-source dependency."""
    response = FallbackInsightGenerator.generate(request)
    has_single_source_risk = any(
        "single-source" in risk.lower()
        for risk in response.key_risks
    )
    assert has_single_source_risk
```

## Metrics for Prompt Quality

| Metric | Target | Measurement |
|--------|--------|-------------|
| Valid JSON rate | >99% | Parse success rate |
| Schema compliance | 100% | Pydantic validation pass |
| Hallucination rate | <5% | Manual review sample |
| Response time | <5s | p95 latency |
| Risk accuracy | >90% | Comparison with rule-based |
