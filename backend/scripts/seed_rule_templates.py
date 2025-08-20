#!/usr/bin/env python3
"""
Script to seed initial categorization rule templates
Run this after database migration to populate default templates
"""

import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.rule_template_service import RuleTemplateService

async def seed_default_templates():
    """Seed database with default categorization rule templates"""
    
    print("🌱 Starting rule template seeding...")
    
    db: Session = SessionLocal()
    try:
        template_service = RuleTemplateService(db)
        
        # Check if templates already exist
        existing_templates = template_service.get_official_templates()
        if existing_templates:
            print(f"ℹ️  Found {len(existing_templates)} existing official templates, skipping seed")
            return
        
        print("📦 Creating default categorization rule templates...")
        
        # Create default templates
        created_templates = template_service.create_default_templates()
        
        print(f"✅ Successfully created {len(created_templates)} default templates:")
        for template in created_templates:
            print(f"   - {template.name} ({template.category})")
        
        # Create some additional useful templates
        additional_templates = [
            {
                "name": "Large Restaurant Bills",
                "description": "Categorize large restaurant and dining expenses",
                "category": "Dining",
                "conditions_template": {
                    "merchant_contains": ["restaurant", "bistro", "grill", "diner", "tavern", "eatery"],
                    "amount_range": {"min_cents": 5000}  # $50+
                },
                "actions_template": {
                    "set_category_id": "{{dining_category_id}}",
                    "add_tags": ["restaurant", "dining out"],
                    "set_confidence": 0.85
                }
            },
            {
                "name": "Pharmacy and Health",
                "description": "Automatically categorize pharmacy and healthcare purchases",
                "category": "Healthcare",
                "conditions_template": {
                    "merchant_contains": ["cvs", "walgreens", "pharmacy", "rite aid", "medical", "clinic", "hospital"]
                },
                "actions_template": {
                    "set_category_id": "{{healthcare_category_id}}",
                    "add_tags": ["pharmacy", "healthcare"],
                    "set_confidence": 0.9
                }
            },
            {
                "name": "Online Shopping",
                "description": "Categorize online shopping from major retailers",
                "category": "Shopping",
                "conditions_template": {
                    "merchant_contains": ["ebay", "etsy", "shopify", "paypal", "square"],
                    "description_contains": ["online", "web", "purchase"]
                },
                "actions_template": {
                    "set_category_id": "{{shopping_category_id}}",
                    "add_tags": ["online shopping", "retail"],
                    "set_confidence": 0.75
                }
            },
            {
                "name": "Utility Bills",
                "description": "Automatically categorize utility payments",
                "category": "Utilities",
                "conditions_template": {
                    "merchant_contains": ["electric", "gas", "water", "utility", "power", "energy"],
                    "amount_range": {"min_cents": 2000, "max_cents": 50000}  # $20-$500
                },
                "actions_template": {
                    "set_category_id": "{{utilities_category_id}}",
                    "add_tags": ["utilities", "bills"],
                    "set_confidence": 0.95
                }
            },
            {
                "name": "Banking Fees",
                "description": "Categorize bank fees and charges",
                "category": "Fees",
                "conditions_template": {
                    "description_contains": ["fee", "charge", "overdraft", "atm", "maintenance"],
                    "amount_range": {"min_cents": 100, "max_cents": 5000}  # $1-$50
                },
                "actions_template": {
                    "set_category_id": "{{fees_category_id}}",
                    "add_tags": ["bank fees", "charges"],
                    "set_confidence": 0.9
                }
            },
            {
                "name": "Transportation - Uber/Lyft",
                "description": "Categorize rideshare services",
                "category": "Transportation",
                "conditions_template": {
                    "merchant_contains": ["uber", "lyft", "taxi", "cab"]
                },
                "actions_template": {
                    "set_category_id": "{{transportation_category_id}}",
                    "add_tags": ["rideshare", "transportation"],
                    "set_confidence": 0.95
                }
            },
            {
                "name": "Professional Services",
                "description": "Categorize payments to professional services",
                "category": "Professional Services",
                "conditions_template": {
                    "merchant_contains": ["law", "attorney", "accountant", "consultant", "professional"],
                    "amount_range": {"min_cents": 10000}  # $100+
                },
                "actions_template": {
                    "set_category_id": "{{professional_services_category_id}}",
                    "add_tags": ["professional", "services"],
                    "set_confidence": 0.8
                }
            },
            {
                "name": "Pet Expenses",
                "description": "Categorize pet-related expenses",
                "category": "Pets",
                "conditions_template": {
                    "merchant_contains": ["pet", "vet", "veterinary", "animal", "petco", "petsmart"]
                },
                "actions_template": {
                    "set_category_id": "{{pets_category_id}}",
                    "add_tags": ["pets", "animals"],
                    "set_confidence": 0.9
                }
            }
        ]
        
        # Create additional templates
        additional_created = []
        for template_data in additional_templates:
            try:
                template = template_service.create_template(
                    name=template_data["name"],
                    description=template_data["description"],
                    category=template_data["category"],
                    conditions_template=template_data["conditions_template"],
                    actions_template=template_data["actions_template"],
                    is_official=True,
                    default_priority=100
                )
                additional_created.append(template)
            except Exception as e:
                print(f"⚠️  Failed to create template {template_data['name']}: {e}")
        
        print(f"✅ Successfully created {len(additional_created)} additional templates:")
        for template in additional_created:
            print(f"   - {template.name} ({template.category})")
        
        total_created = len(created_templates) + len(additional_created)
        print(f"🎉 Template seeding completed! Created {total_created} total templates.")
        
        # Print template statistics
        all_templates = template_service.get_official_templates()
        categories = template_service.get_template_categories()
        
        print(f"\n📊 Template Statistics:")
        print(f"   - Total official templates: {len(all_templates)}")
        print(f"   - Categories: {len(categories)}")
        print(f"   - Categories list: {', '.join(sorted(categories))}")
        
    except Exception as e:
        print(f"❌ Error during template seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

async def main():
    """Main entry point"""
    try:
        await seed_default_templates()
        print("\n✅ Rule template seeding completed successfully!")
    except Exception as e:
        print(f"\n❌ Rule template seeding failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())