import uuid
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from sqlalchemy.sql.functions import sqlutil

class ProjectCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )
    slug: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime
