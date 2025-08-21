"""
Service for managing categorization rule templates
Provides template management and rule creation from templates
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from uuid import UUID

from app.config import Settings, settings
from app.models.categorization_rule_template import CategorizationRuleTemplate
from app.models.categorization_rule import CategorizationRule
from app.models.category import Category

logger = logging.getLogger(__name__)

class RuleTemplateService:
    """Engine service for managing categorization rule templates"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
    
    async def get_official_templates(self, db: Session, category_filter: Optional[str] = None) -> List[CategorizationRuleTemplate]:
        """Get official rule templates"""
        
        query = db.query(CategorizationRuleTemplate).filter(
            CategorizationRuleTemplate.is_official == True
        )
        
        if category_filter:
            query = query.filter(CategorizationRuleTemplate.category == category_filter)
        
        return query.order_by(
            desc(CategorizationRuleTemplate.popularity_score)
        ).all()
    
    async def get_popular_templates(self, db: Session, limit: int = 20, category_filter: Optional[str] = None) -> List[CategorizationRuleTemplate]:
        """Get most popular community templates"""
        
        query = db.query(CategorizationRuleTemplate)
        
        if category_filter:
            query = query.filter(CategorizationRuleTemplate.category == category_filter)
        
        return query.order_by(
            desc(CategorizationRuleTemplate.popularity_score),
            desc(CategorizationRuleTemplate.times_used)
        ).limit(limit).all()
    
    async def get_templates_by_category(self, db: Session) -> Dict[str, List[CategorizationRuleTemplate]]:
        """Get templates grouped by category"""
        
        templates = db.query(CategorizationRuleTemplate).order_by(
            CategorizationRuleTemplate.category,
            desc(CategorizationRuleTemplate.popularity_score)
        ).all()
        
        grouped = {}
        for template in templates:
            if template.category not in grouped:
                grouped[template.category] = []
            grouped[template.category].append(template)
        
        return grouped
    
    async def get_template_by_id(self, db: Session, template_id: UUID) -> Optional[CategorizationRuleTemplate]:
        """Get a specific template by ID"""
        
        return db.query(CategorizationRuleTemplate).filter(
            CategorizationRuleTemplate.id == template_id
        ).first()
    
    async def create_rule_from_template(
        self, 
        db: Session,
        template_id: UUID, 
        user_id: UUID, 
        customizations: Optional[Dict[str, Any]] = None
    ) -> CategorizationRule:
        """Create a user rule from a template"""
        
        template = await self.get_template_by_id(db, template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Validate customizations
        if customizations:
            validation_errors = template.validate_customizations(customizations)
            if validation_errors:
                raise ValueError(f"Invalid customizations: {', '.join(validation_errors)}")
        
        # Create conditions and actions from template
        conditions = template.create_conditions_for_user(customizations)
        actions = template.create_actions_for_user(customizations)
        
        # Validate that target category exists and belongs to user
        target_category_id = actions.get("set_category_id")
        if target_category_id:
            category = db.query(Category).filter(
                and_(
                    Category.id == target_category_id,
                    Category.user_id == user_id
                )
            ).first()
            if not category:
                raise ValueError(f"Target category {target_category_id} not found or doesn't belong to user")
        
        # Create the rule
        rule = CategorizationRule(
            user_id=user_id,
            name=customizations.get("name", template.name),
            description=f"Created from template: {template.name}",
            priority=template.default_priority,
            conditions=conditions,
            actions=actions,
            template_id=template.id,
            template_version=template.version,
            is_active=True
        )
        
        db.add(rule)
        
        # Update template usage tracking
        template.increment_usage()
        db.add(template)
        
        db.commit()
        db.refresh(rule)
        
        logger.info(f"Created rule {rule.id} from template {template.id} for user {user_id}")
        
        return rule
    
    async def suggest_templates_for_user(self, db: Session, user_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Suggest templates based on user's transaction patterns"""
        
        try:
            # This is a simplified implementation
            # In a more sophisticated version, we would analyze the user's transactions
            # to find patterns and suggest relevant templates
            
            # For now, return popular templates with some basic scoring
            popular_templates = await self.get_popular_templates(db, limit * 2)
            
            suggestions = []
            for template in popular_templates[:limit]:
                suggestion = {
                    "template_id": str(template.id),
                    "name": template.name,
                    "description": template.description,
                    "category": template.category,
                    "popularity_score": template.popularity_score,
                    "times_used": template.times_used,
                    "success_rating": template.success_rating,
                    "is_official": template.is_official,
                    "required_customizations": template.get_required_customizations(),
                    "recommendation_reason": self._get_recommendation_reason(template, user_id)
                }
                suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to suggest templates for user {user_id}: {e}")
            return []
    
    def _get_recommendation_reason(self, template: CategorizationRuleTemplate, user_id: UUID) -> str:
        """Generate a recommendation reason for a template"""
        
        if template.is_official:
            return "Official template recommended for all users"
        elif template.popularity_score > 1000:
            return "Highly popular template used by many users"
        elif template.success_rating and template.success_rating > 0.8:
            return f"High success rate ({template.success_rating_percentage:.0f}%)"
        else:
            return "Popular community template"
    
    async def create_template(
        self,
        db: Session,
        name: str,
        description: str,
        category: str,
        conditions_template: Dict[str, Any],
        actions_template: Dict[str, Any],
        created_by_user_id: Optional[UUID] = None,
        is_official: bool = False,
        default_priority: int = 100,
        tags: Optional[List[str]] = None
    ) -> CategorizationRuleTemplate:
        """Create a new rule template"""
        
        template = CategorizationRuleTemplate(
            name=name,
            description=description,
            category=category,
            conditions_template=conditions_template,
            actions_template=actions_template,
            created_by_user_id=created_by_user_id,
            is_official=is_official,
            default_priority=default_priority,
            tags=tags or []
        )
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        logger.info(f"Created template {template.id}: {name}")
        
        return template
    
    async def update_template_rating(self, db: Session, template_id: UUID, rating: float) -> CategorizationRuleTemplate:
        """Update template success rating with user feedback"""
        
        template = await self.get_template_by_id(db, template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        if not 0.0 <= rating <= 1.0:
            raise ValueError("Rating must be between 0.0 and 1.0")
        
        template.update_success_rating(rating)
        db.add(template)
        db.commit()
        db.refresh(template)
        
        logger.info(f"Updated template {template_id} rating to {rating}")
        
        return template
    
    async def get_template_categories(self, db: Session) -> List[str]:
        """Get list of all template categories"""
        
        result = db.query(CategorizationRuleTemplate.category).distinct().all()
        return [row[0] for row in result]
    
    async def search_templates(
        self, 
        db: Session,
        query: str, 
        category_filter: Optional[str] = None,
        limit: int = 20
    ) -> List[CategorizationRuleTemplate]:
        """Search templates by name or description"""
        
        search_query = db.query(CategorizationRuleTemplate)
        
        # Text search
        if query:
            search_term = f"%{query}%"
            search_query = search_query.filter(
                or_(
                    CategorizationRuleTemplate.name.ilike(search_term),
                    CategorizationRuleTemplate.description.ilike(search_term)
                )
            )
        
        # Category filter
        if category_filter:
            search_query = search_query.filter(
                CategorizationRuleTemplate.category == category_filter
            )
        
        return search_query.order_by(
            desc(CategorizationRuleTemplate.popularity_score)
        ).limit(limit).all()
    
    async def get_template_statistics(self, db: Session) -> Dict[str, Any]:
        """Get overall template statistics"""
        
        total_templates = db.query(CategorizationRuleTemplate).count()
        official_templates = db.query(CategorizationRuleTemplate).filter(
            CategorizationRuleTemplate.is_official == True
        ).count()
        
        # Most popular template
        most_popular = db.query(CategorizationRuleTemplate).order_by(
            desc(CategorizationRuleTemplate.popularity_score)
        ).first()
        
        # Category distribution
        category_counts = db.query(
            CategorizationRuleTemplate.category,
            func.count(CategorizationRuleTemplate.id)
        ).group_by(CategorizationRuleTemplate.category).all()
        
        category_distribution = {category: count for category, count in category_counts}
        
        return {
            "total_templates": total_templates,
            "official_templates": official_templates,
            "community_templates": total_templates - official_templates,
            "categories": len(category_distribution),
            "category_distribution": category_distribution,
            "most_popular_template": {
                "id": str(most_popular.id),
                "name": most_popular.name,
                "popularity_score": most_popular.popularity_score,
                "times_used": most_popular.times_used
            } if most_popular else None
        }
    
    async def create_default_templates(self, db: Session) -> List[CategorizationRuleTemplate]:
        """Create default official templates for common transaction patterns"""
        
        default_templates = [
            {
                "name": "Coffee Shop Purchases",
                "description": "Automatically categorize coffee shop transactions to dining",
                "category": "Dining",
                "conditions_template": {
                    "merchant_contains": ["starbucks", "dunkin", "coffee", "cafe", "espresso"]
                },
                "actions_template": {
                    "set_category_id": "{{dining_category_id}}",
                    "add_tags": ["coffee", "beverages"],
                    "set_confidence": 0.9
                }
            },
            {
                "name": "Gas Station Purchases",
                "description": "Automatically categorize gas station transactions to transportation",
                "category": "Transportation",
                "conditions_template": {
                    "merchant_contains": ["shell", "exxon", "chevron", "bp", "gas", "fuel"]
                },
                "actions_template": {
                    "set_category_id": "{{transportation_category_id}}",
                    "add_tags": ["fuel", "gas"],
                    "set_confidence": 0.95
                }
            },
            {
                "name": "Grocery Store Purchases",
                "description": "Automatically categorize grocery store transactions to groceries",
                "category": "Groceries",
                "conditions_template": {
                    "merchant_contains": ["walmart", "target", "kroger", "safeway", "whole foods", "grocery"]
                },
                "actions_template": {
                    "set_category_id": "{{groceries_category_id}}",
                    "add_tags": ["groceries", "food"],
                    "set_confidence": 0.85
                }
            },
            {
                "name": "Streaming Services",
                "description": "Automatically categorize streaming service subscriptions to entertainment",
                "category": "Entertainment",
                "conditions_template": {
                    "merchant_contains": ["netflix", "spotify", "hulu", "disney", "amazon prime", "youtube premium"],
                    "amount_range": {"min_cents": 500, "max_cents": 5000}
                },
                "actions_template": {
                    "set_category_id": "{{entertainment_category_id}}",
                    "add_tags": ["streaming", "subscription"],
                    "set_confidence": 0.95
                }
            },
            {
                "name": "Large Amazon Purchases",
                "description": "Categorize large Amazon purchases as shopping",
                "category": "Shopping",
                "conditions_template": {
                    "merchant_contains": ["amazon", "amzn"],
                    "amount_range": {"min_cents": 5000}
                },
                "actions_template": {
                    "set_category_id": "{{shopping_category_id}}",
                    "add_tags": ["amazon", "online shopping"],
                    "set_confidence": 0.8
                }
            }
        ]
        
        created_templates = []
        for template_data in default_templates:
            try:
                template = await self.create_template(
                    db=db,
                    name=template_data["name"],
                    description=template_data["description"],
                    category=template_data["category"],
                    conditions_template=template_data["conditions_template"],
                    actions_template=template_data["actions_template"],
                    is_official=True,
                    default_priority=100
                )
                created_templates.append(template)
            except Exception as e:
                logger.error(f"Failed to create default template {template_data['name']}: {e}")
        
        logger.info(f"Created {len(created_templates)} default templates")
        return created_templates