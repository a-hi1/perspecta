"""Style profile model for user writing style learning."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StyleProfile(Base):
    """Learned writing style profile from user's historical posts."""

    __tablename__ = "style_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, index=True
    )

    # Sentence analysis
    avg_sentence_length: Mapped[float] = mapped_column(Float, default=0.0)
    sentence_length_variance: Mapped[float] = mapped_column(Float, default=0.0)

    # Structure patterns
    avg_paragraph_count: Mapped[float] = mapped_column(Float, default=0.0)
    avg_paragraph_length: Mapped[float] = mapped_column(Float, default=0.0)
    preferred_opening_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_closing_style: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Language features
    emoji_frequency: Mapped[float] = mapped_column(Float, default=0.0)
    emoji_types: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    technical_term_density: Mapped[float] = mapped_column(Float, default=0.0)
    common_phrases: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Tone analysis
    formality_score: Mapped[float] = mapped_column(Float, default=0.5)
    enthusiasm_score: Mapped[float] = mapped_column(Float, default=0.5)
    storytelling_score: Mapped[float] = mapped_column(Float, default=0.5)

    # Content patterns
    typical_structure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hashtag_style: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mention_frequency: Mapped[float] = mapped_column(Float, default=0.0)

    # Training data
    sample_post_count: Mapped[int] = mapped_column(Integer, default=0)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sample_posts_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="style_profile")

    def __repr__(self) -> str:
        return f"<StyleProfile for user={self.user_id[:8]}>"

    def to_style_prompt_context(self) -> str:
        """Convert profile to a prompt context string for style adaptation."""
        return f"""User Writing Style Profile:
- Average sentence length: {self.avg_sentence_length:.0f} words
- Paragraph count: typically {self.avg_paragraph_count:.0f} paragraphs
- Opening style: {self.preferred_opening_style or 'varied'}
- Closing style: {self.preferred_closing_style or 'varied'}
- Emoji usage: {'frequent' if self.emoji_frequency > 0.3 else 'moderate' if self.emoji_frequency > 0.1 else 'minimal'}
- Technical term density: {'high' if self.technical_term_density > 0.3 else 'moderate' if self.technical_term_density > 0.1 else 'low'}
- Formality: {'formal' if self.formality_score > 0.7 else 'casual' if self.formality_score < 0.3 else 'balanced'}
- Enthusiasm: {'high' if self.enthusiasm_score > 0.7 else 'moderate'}
- Storytelling: {'strong' if self.storytelling_score > 0.7 else 'moderate' if self.storytelling_score > 0.3 else 'minimal'}
- Common phrases: {', '.join((self.common_phrases or {}).keys())[:200]}
"""
