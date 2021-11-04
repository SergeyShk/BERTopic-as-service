from typing import List, Optional

from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel


class TopicModelBase(SQLModel):
    model_id: UUID
    version: int = 1


class TopicModel(TopicModelBase, table=True):
    __tablename__ = "topic_model"

    id: Optional[int] = Field(default=None, primary_key=True)  # NOQA: A003
    topics: List["Topic"] = Relationship(
        back_populates="topic_model", sa_relationship_kwargs={"cascade": "all,delete"}
    )


class WordBase(SQLModel):
    name: str
    score: float


class Word(WordBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)  # NOQA: A003
    topic_id: int = Field(foreign_key="topic.id")
    topic: "Topic" = Relationship(
        back_populates="top_words", sa_relationship_kwargs={"cascade": "all,delete"}
    )


class TopicBase(SQLModel):
    name: str
    count: int
    topic_index: int


class TopicWithWords(TopicBase):
    top_words: List["WordBase"] = []


class Topic(TopicBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)  # NOQA: A003
    topic_model_id: int = Field(foreign_key="topic_model.id")
    top_words: List[Word] = Relationship(
        back_populates="topic", sa_relationship_kwargs={"cascade": "all,delete"}
    )
    topic_model: TopicModel = Relationship(
        back_populates="topics", sa_relationship_kwargs={"cascade": "all,delete"}
    )
