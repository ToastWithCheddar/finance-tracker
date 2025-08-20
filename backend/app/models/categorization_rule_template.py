# Standard library imports
from typing import Optional, Dict, Any
from uuid import UUID

# Third-party imports
from sqlalchemy import String, BigInteger, Boolean, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, relationship, mapped_column

# Local imports
from .base import BaseModel

class CategorizationRuleTemplate(BaseModel):
    """Pre-built categorization rule templates"""
    __tablename__ = "categorization_rule_templates"
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # "Shopping", "Dining", etc.
    
    # Template rule structure
    conditions_template: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    actions_template: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # Template metadata
    popularity_score: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    
    # Version control
    version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    parent_template_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    
    # Usage tracking
    times_used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    success_rating: Mapped[Optional[float]] = mapped_column(nullable=True)  # Average user rating
    
    # Template configuration
    default_priority: Mapped[int] = mapped_column(BigInteger, default=100, nullable=False)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # Tags for categorizing templates
    
    __table_args__ = (
        Index('idx_template_category', 'category'),
        Index('idx_template_official', 'is_official'),
        Index('idx_template_popularity', 'popularity_score', 'times_used'),
        Index('idx_template_created_by', 'created_by_user_id'),
        Index('idx_template_parent', 'parent_template_id'),
        Index('idx_template_tags', 'tags'),
    )
    
    @property
    def is_community_template(self) -> bool:
        """Check if this is a community-created template"""
        return not self.is_official and self.created_by_user_id is not None
    
    @property
    def success_rating_percentage(self) -> Optional[float]:
        """Get success rating as percentage"""
        return self.success_rating * 100 if self.success_rating is not None else None
    
    def increment_usage(self):
        """Increment usage counter when template is used"""
        self.times_used += 1
        # Simple popularity score calculation: times_used + (success_rating * 100)
        rating_bonus = int((self.success_rating or 0.5) * 100)
        self.popularity_score = self.times_used + rating_bonus
    
    def update_success_rating(self, new_rating: float):
        """Update success rating with new user feedback (0.0 to 1.0)"""
        if self.success_rating is None:
            self.success_rating = new_rating
        else:
            # Weighted average with more weight on recent ratings
            weight = 0.2  # 20% weight for new rating
            self.success_rating = (1 - weight) * self.success_rating + weight * new_rating
    
    def create_conditions_for_user(self, customizations: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create conditions dict for user, applying any customizations"""
        conditions = self.conditions_template.copy()
        
        if customizations:
            # Apply customizations to conditions
            for key, value in customizations.items():
                if key.startswith("condition_"):
                    condition_key = key.replace("condition_", "")
                    conditions[condition_key] = value
        
        return conditions
    
    def create_actions_for_user(self, customizations: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create actions dict for user, applying any customizations"""
        actions = self.actions_template.copy()
        
        if customizations:
            # Apply customizations to actions
            for key, value in customizations.items():
                if key.startswith("action_"):
                    action_key = key.replace("action_", "")
                    actions[action_key] = value
                elif key == "target_category_id":
                    actions["set_category_id"] = str(value)
        
        return actions
    
    def get_required_customizations(self) -> list:
        """Get list of required customizations for this template"""
        required = []
        
        # Check if template requires category selection
        if not self.actions_template.get("set_category_id"):
            required.append("target_category_id")
        
        # Check for placeholder values in conditions that need customization
        for key, value in self.conditions_template.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                required.append(f"condition_{key}")
            elif isinstance(value, list) and any(
                isinstance(v, str) and v.startswith("{{") and v.endswith("}}")
                for v in value
            ):
                required.append(f"condition_{key}")
        
        return required
    
    def validate_customizations(self, customizations: Dict[str, Any]) -> list:
        """Validate customizations and return list of errors"""
        errors = []
        required = self.get_required_customizations()
        
        # Check required customizations
        for req in required:
            if req not in customizations:
                errors.append(f"Missing required customization: {req}")
        
        # Validate specific customization formats
        if "target_category_id" in customizations:
            try:
                UUID(customizations["target_category_id"])
            except (ValueError, TypeError):
                errors.append("target_category_id must be a valid UUID")
        
        return errors
    
    def __repr__(self) -> str:
        return (
            f"<CategorizationRuleTemplate("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"category='{self.category}', "
            f"official={self.is_official}, "
            f"used={self.times_used} times)>"
        )