"""Document model for indexed files."""

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, ForeignKey, String, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gdrive_rag.models.base import Base

if TYPE_CHECKING:
    from gdrive_rag.models.chunk import Chunk
    from gdrive_rag.models.source import Source


class Document(Base):
    __tablename__ = "documents"

    file_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    web_view_link: Mapped[str] = mapped_column(Text, nullable=False)
    modified_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    owners: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    parents: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    source: Mapped["Source"] = relationship(back_populates="documents")
    chunks: Mapped[List["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
