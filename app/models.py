"""
Pydantic Models for Supplier Sourcing Insights API

This module defines the data models for input validation and output schema enforcement.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class RiskLevel(str, Enum):
    """Enumeration for standardized risk level classifications."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class Supplier(BaseModel):
    """
    Individual supplier data model with comprehensive validation.
    
    Attributes:
        supplier_name: Unique identifier for the supplier
        annual_spend_usd: Total annual procurement spend in USD (must be positive)
        on_time_delivery_pct: Delivery performance as percentage (0-100)
        contract_expiry_months: Months until contract renewal
        single_source_dependency: Whether this is the only supplier for critical items
        region: Geographic region of the supplier
    """
    supplier_name: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Name of the supplier"
    )
    annual_spend_usd: float = Field(
        ..., 
        gt=0,
        description="Annual spend with supplier in USD"
    )
    on_time_delivery_pct: float = Field(
        ..., 
        ge=0, 
        le=100,
        description="On-time delivery percentage (0-100)"
    )
    contract_expiry_months: int = Field(
        ..., 
        ge=0,
        description="Months until contract expiration"
    )
    single_source_dependency: bool = Field(
        ...,
        description="Whether this supplier is a single source for critical items"
    )
    region: str = Field(
        ..., 
        min_length=1,
        description="Geographic region of the supplier"
    )

    @field_validator('on_time_delivery_pct', mode='before')
    @classmethod
    def convert_decimal_to_percentage(cls, v):
        """Convert decimal format (0.92) to percentage (92) if needed."""
        if isinstance(v, (int, float)) and 0 <= v <= 1:
            return v * 100
        return v


class InsightRequest(BaseModel):
    """
    Input payload for generating sourcing insights.
    
    Attributes:
        category: The procurement category
        suppliers: List of supplier data objects
    """
    category: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Procurement category name",
        examples=["IT Hardware", "Raw Materials", "Logistics Services"]
    )
    suppliers: List[Supplier] = Field(
        ..., 
        min_length=1,
        description="List of suppliers with their data"
    )

    @model_validator(mode='after')
    def validate_suppliers_not_empty(self):
        """At least one supplier should be provided."""
        if not self.suppliers:
            raise ValueError("At least one supplier must be provided")
        return self

    @property
    def total_spend(self) -> float:
        """Calculating total spend."""
        return sum(s.annual_spend_usd for s in self.suppliers)

    @property
    def supplier_count(self) -> int:
        """Get the number of suppliers."""
        return len(self.suppliers)


class InsightResponse(BaseModel):
    """
    Output schema for sourcing insights.
    """
    category: str = Field(
        ...,
        description="The procurement category analyzed"
    )
    overall_risk_level: RiskLevel = Field(
        ...,
        description="Aggregated risk assessment: Low, Medium, or High"
    )
    key_risks: List[str] = Field(
        ..., 
        min_length=1,
        max_length=10,
        description="List of identified risk factors"
    )
    negotiation_levers: List[str] = Field(
        ..., 
        min_length=1,
        max_length=10,
        description="Strategic negotiation opportunities"
    )
    recommended_actions_next_90_days: List[str] = Field(
        ..., 
        min_length=1,
        max_length=10,
        description="Prioritized action items for the next quarter"
    )
    confidence_score: float = Field(
        ..., 
        ge=0, 
        le=1,
        description="Model confidence in the analysis (0.0 to 1.0)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "category": "IT Hardware",
                "overall_risk_level": "Medium",
                "key_risks": [
                    "Single-source dependency on TechSource Inc. ($4.2M annual spend)",
                    "GlobalComp Solutions contract expires in 3 months"
                ],
                "negotiation_levers": [
                    "Strong delivery performance (97%) from NextGen Systems",
                    "Multi-supplier strategy reduces bargaining pressure"
                ],
                "recommended_actions_next_90_days": [
                    "Initiate contract renewal negotiations with GlobalComp Solutions",
                    "Develop contingency supplier for TechSource Inc. dependency"
                ],
                "confidence_score": 0.85
            }
        }
    }


class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(..., description="Error type identifier")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error context")


class HealthResponse(BaseModel):
    """Health check endpoint."""
    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="API version")
    llm_provider: str = Field(..., description="Configured LLM provider")
