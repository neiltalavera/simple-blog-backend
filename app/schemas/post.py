from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import UserRead


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=50000)


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1, max_length=50000)


class PostRead(BaseModel):
    id: int
    title: str
    body: str
    author: UserRead
    created_at: datetime
    updated_at: datetime
    reaction_count: int = 0
    comment_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommentRead(BaseModel):
    id: int
    post_id: int
    author_id: int
    body: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
