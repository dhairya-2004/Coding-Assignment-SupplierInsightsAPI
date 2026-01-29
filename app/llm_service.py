import json
import os
import re
from typing import Optional
import httpx

from app.models import InsightRequest, InsightResponse, RiskLevel


def build_system_prompt() -> str:
    return """You are an expert procurement analyst specializing in supplier risk assessment.

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

Respond ONLY with JSON, no markdown or extra text."""


def build_user_prompt(request: InsightRequest) -> str:
    total_spend = request.total_spend
    suppliers_data = []
    
    for s in request.suppliers:
        suppliers_data.append({
            "supplier_name": s.supplier_name,
            "annual_spend_usd": s.annual_spend_usd,
            "spend_share_pct": round((s.annual_spend_usd / total_spend) * 100, 1),
            "on_time_delivery_pct": s.on_time_delivery_pct,
            "contract_expiry_months": s.contract_expiry_months,
            "single_source_dependency": s.single_source_dependency,
            "region": s.region
        })
    
    return f"""Analyze supplier data for "{request.category}":

{json.dumps(suppliers_data, indent=2)}

SUMMARY:
- Total Spend: ${total_spend:,.0f}
- Suppliers: {request.supplier_count}
- Regions: {', '.join(set(s.region for s in request.suppliers))}
- Single-Source: {sum(1 for s in request.suppliers if s.single_source_dependency)}

Generate insights JSON."""


def parse_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            return json.loads(match.group())
        raise ValueError("Failed to parse JSON")


def validate_response(data: dict, request: InsightRequest) -> InsightResponse:
    risk_map = {"low": RiskLevel.LOW, "medium": RiskLevel.MEDIUM, "high": RiskLevel.HIGH}
    risk_level = risk_map.get(data.get("overall_risk_level", "Medium").lower(), RiskLevel.MEDIUM)
    
    confidence = max(0.0, min(1.0, float(data.get("confidence_score", 0.7))))
    
    return InsightResponse(
        category=request.category,
        overall_risk_level=risk_level,
        key_risks=data.get("key_risks", ["No risks identified"])[:10],
        negotiation_levers=data.get("negotiation_levers", ["Review contracts"])[:10],
        recommended_actions_next_90_days=data.get("recommended_actions_next_90_days", ["Conduct review"])[:10],
        confidence_score=round(confidence, 2)
    )


class GroqService:
    """
    Models: llama-3.3-70b-versatile
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.3
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.temperature = temperature
        self.base_url = "https://api.groq.com/openai/v1"
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY required. Get free key at https://console.groq.com/keys")

    async def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Call Groq API (OpenAI-compatible format)"""
        
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"Groq API error {response.status_code}: {response.text}")
            
            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def generate_insights(self, request: InsightRequest) -> InsightResponse:
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(request)
        
        raw = await self._call_api(system_prompt, user_prompt)
        data = parse_response(raw)
        response = validate_response(data, request)
        response.confidence_score = min(0.95, response.confidence_score + 0.2)
        return response



GeminiService = GroqService


class FallbackInsightGenerator:
    """Rule-based fallback when LLM unavailable"""
    
    @staticmethod
    def generate(request: InsightRequest) -> InsightResponse:
        risks, levers, actions = [], [], []
        total_spend = request.total_spend
        
        for s in request.suppliers:
            pct = (s.annual_spend_usd / total_spend) * 100
            
            if s.single_source_dependency:
                risks.append(f"Single-source: {s.supplier_name} (${s.annual_spend_usd/1e6:.1f}M, {pct:.0f}%)")
            
            if s.contract_expiry_months <= 3:
                risks.append(f"Urgent: {s.supplier_name} expires in {s.contract_expiry_months} months")
                actions.append(f"Renew contract with {s.supplier_name}")
            elif s.contract_expiry_months <= 6:
                actions.append(f"Start renewal talks with {s.supplier_name}")
            
            if s.on_time_delivery_pct < 85:
                risks.append(f"Low delivery: {s.supplier_name} at {s.on_time_delivery_pct:.0f}%")
            
            if s.on_time_delivery_pct >= 95:
                levers.append(f"Top performer: {s.supplier_name} ({s.on_time_delivery_pct:.0f}%)")
            
            if pct >= 30:
                levers.append(f"Volume leverage: {s.supplier_name} ({pct:.0f}% spend)")
        
        high_risk = any(s.single_source_dependency and s.annual_spend_usd/total_spend > 0.4 for s in request.suppliers)
        high_risk = high_risk or any(s.contract_expiry_months <= 3 for s in request.suppliers)
        high_risk = high_risk or any(s.on_time_delivery_pct < 80 for s in request.suppliers)
        
        med_risk = any(s.contract_expiry_months <= 6 for s in request.suppliers)
        med_risk = med_risk or any(s.on_time_delivery_pct < 90 for s in request.suppliers)
        
        if high_risk:
            level = RiskLevel.HIGH
        elif med_risk:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
        
        return InsightResponse(
            category=request.category,
            overall_risk_level=level,
            key_risks=risks[:5] or ["No critical risks identified"],
            negotiation_levers=levers[:5] or ["Review contracts for opportunities"],
            recommended_actions_next_90_days=actions[:5] or ["Quarterly supplier review"],
            confidence_score=0.65
        )