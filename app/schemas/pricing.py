from typing import Optional

from pydantic import BaseModel, Field


class ChatModelPricing(BaseModel):
    model: str
    prompt_per_million: float
    completion_per_million: float


class EmbeddingModelPricing(BaseModel):
    model: str
    price_per_million: float


class PricingDefaults(BaseModel):
    chat_prompt_per_million: float
    chat_completion_per_million: float
    embedding_per_million: float


class TokenBilling(BaseModel):
    currency: str
    rate_per_token: float
    unit: str
    note: str


class PricingTableResponse(BaseModel):
    currency: str
    effective_date: str
    unit: str
    source: str
    is_estimate: bool
    note: str
    defaults: PricingDefaults
    billing: TokenBilling
    chat_models: list[ChatModelPricing] = Field(default_factory=list)
    embedding_models: list[EmbeddingModelPricing] = Field(default_factory=list)


class UserTokenUsage(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    end_user: Optional[str] = None
    answers: int = 0
    cached_answers: int = 0
    uncached_answers: int = 0
    total_tokens: int = 0
    billable_tokens: int = 0
    cost_inr: float = 0.0


class UserTokenUsageResponse(BaseModel):
    #: "all" for admins, "own" for everyone else.
    scope: str = "all"
    currency: str
    rate_per_token: float
    unit: str
    note: str
    total_billable_tokens: int
    total_cost_inr: float
    items: list[UserTokenUsage] = Field(default_factory=list)
