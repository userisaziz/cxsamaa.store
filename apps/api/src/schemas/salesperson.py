from pydantic import BaseModel


class SalespersonCreate(BaseModel):
    store_id: str
    name: str
    email: str | None = None
    role: str | None = None
    shift: str | None = None
    device_number: str | None = None


class SalespersonUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    role: str | None = None
    shift: str | None = None
    device_number: str | None = None


class SalespersonResponse(BaseModel):
    id: str
    store_id: str
    name: str
    email: str | None = None
    role: str | None = None
    shift: str | None = None
    device_number: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class SalespersonPerformanceResponse(BaseModel):
    salesperson_id: str
    name: str
    total_conversations: int
    avg_greeting_score: float | None = None
    avg_discovery_score: float | None = None
    avg_product_knowledge_score: float | None = None
    avg_objection_handling_score: float | None = None
    avg_closing_score: float | None = None
    avg_overall_score: float | None = None
    conversion_rate: float | None = None
