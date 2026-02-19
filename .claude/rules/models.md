# Pydantic Model Rules

## Field Descriptions
Every Pydantic field MUST have `Field(description=...)`:
```python
class AuditReport(BaseModel):
    url: str = Field(description="The audited URL")
    score: float = Field(description="Overall AEO score (0-100)")
```
This propagates descriptions to MCP tool schemas automatically.

## Model Location
ALL data contracts live in `core/models.py`. No model definitions elsewhere.

## Conventions
- Use Pydantic v2 syntax
- Use `model_validator` for cross-field validation
- Export enums from models.py (e.g., OutputFormat)
- Use `Field(ge=0, le=100)` for score bounds where appropriate
