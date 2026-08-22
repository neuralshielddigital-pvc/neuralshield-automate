from app.core.database import SessionLocal
from app.models.workflow_template import WorkflowTemplate

templates = [
    {
        "name": "Lead Capture → Email Alert",
        "is_featured": True,
        "is_new": False,
        "install_count": 0,
        "difficulty": "Beginner",
        "estimated_setup_minutes": 5,
        "tags": ['lead', 'email', 'webhook'],
        "description": "Capture webhook lead data and send an email notification.",
        "category": "Lead Automation",
        "definition": {
            "trigger": {
                "type": "WEBHOOK_RECEIVED",
                "config": {}
            },
            "actions": [
                {
                    "type": "CREATE_LEAD",
                    "config": {
                        "email": "{{email}}",
                        "name": "{{name}}",
                        "phone": "{{phone}}",
                        "source": "{{source}}",
                        "tags": "{{tags}}"
                    }
                },
                {
                    "type": "SEND_EMAIL",
                    "config": {
                        "to": "admin-test@example.com",
                        "subject": "New Lead",
                        "body": "New lead received: {{name}} ({{email}})"
                    }
                }
            ]
        }
    },
    {
        "name": "Webhook → Create Lead",
        "is_featured": False,
        "is_new": False,
        "install_count": 0,
        "difficulty": "Beginner",
        "estimated_setup_minutes": 3,
        "tags": ['lead', 'webhook'],
        "description": "Create a lead from any webhook submission.",
        "category": "Lead Automation",
        "definition": {
            "trigger": {
                "type": "WEBHOOK_RECEIVED",
                "config": {}
            },
            "actions": [
                {
                    "type": "CREATE_LEAD",
                    "config": {
                        "email": "{{email}}",
                        "name": "{{name}}",
                        "phone": "{{phone}}",
                        "source": "webhook",
                        "tags": "{{tags}}"
                    }
                }
            ]
        }
    },
    {
        "name": "Lead Capture → Audit Log",
        "is_featured": False,
        "is_new": False,
        "install_count": 0,
        "difficulty": "Beginner",
        "estimated_setup_minutes": 5,
        "tags": ['lead', 'audit', 'compliance'],
        "description": "Capture a webhook lead and write an audit log entry.",
        "category": "Compliance",
        "definition": {
            "trigger": {
                "type": "WEBHOOK_RECEIVED",
                "config": {}
            },
            "actions": [
                {
                    "type": "CREATE_LEAD",
                    "config": {
                        "email": "{{email}}",
                        "name": "{{name}}",
                        "phone": "{{phone}}",
                        "source": "{{source}}",
                        "tags": "{{tags}}"
                    }
                },
                {
                    "type": "ADD_AUDIT_LOG",
                    "config": {
                        "action": "Lead created from webhook"
                    }
                }
            ]
        }
    },
    {
        "name": "AI Sales Reply → Slack",
        "is_featured": True,
        "is_new": True,
        "install_count": 0,
        "difficulty": "Beginner",
        "estimated_setup_minutes": 8,
        "tags": ['ai', 'sales', 'slack'],
        "description": "Generate a professional AI sales reply from webhook lead data and send it to Slack.",
        "category": "AI Automation",
        "definition": {
            "trigger": {
                "type": "WEBHOOK_RECEIVED",
                "config": {}
            },
            "actions": [
                {
                    "type": "OPENAI_TEXT_GENERATE",
                    "config": {
                        "model": "gpt-4o-mini",
                        "prompt": "Write a short professional sales reply for this lead. Name: {{name}} Email: {{email}} Message: {{message}}",
                        "temperature": 0.3,
                        "max_tokens": 500
                    }
                },
                {
                    "type": "SLACK_SEND_MESSAGE",
                    "config": {
                        "channel": "C0BFTKA5LA2",
                        "message": "AI Sales Reply:\n{{ai_output}}\n\nModel: {{ai_model}}\nTokens: {{ai_total_tokens}}"
                    }
                }
            ]
        }
    },
    {
        "name": "AI Lead Qualification",
        "is_featured": True,
        "is_new": True,
        "install_count": 0,
        "difficulty": "Beginner",
        "estimated_setup_minutes": 7,
        "tags": ['ai', 'lead', 'sales'],
        "description": "Use AI to qualify a webhook lead and write the qualification summary to the audit log.",
        "category": "AI Automation",
        "definition": {
            "trigger": {
                "type": "WEBHOOK_RECEIVED",
                "config": {}
            },
            "actions": [
                {
                    "type": "OPENAI_TEXT_GENERATE",
                    "config": {
                        "model": "gpt-4o-mini",
                        "prompt": "Qualify this lead as Hot, Warm, or Cold. Explain in 2 bullet points. Name: {{name}} Email: {{email}} Message: {{message}}",
                        "temperature": 0.2,
                        "max_tokens": 400
                    }
                },
                {
                    "type": "ADD_AUDIT_LOG",
                    "config": {
                        "action": "AI Lead Qualification: {{ai_output}}"
                    }
                }
            ]
        }
    },
    {
        "name": "AI Slack Summary",
        "is_featured": True,
        "is_new": True,
        "install_count": 0,
        "difficulty": "Intermediate",
        "estimated_setup_minutes": 10,
        "tags": ['ai', 'slack', 'summary'],
        "description": "Summarize an incoming Slack message using AI and post the summary back to Slack.",
        "category": "AI Automation",
        "definition": {
            "trigger": {
                "type": "SLACK_NEW_MESSAGE",
                "config": {}
            },
            "actions": [
                {
                    "type": "OPENAI_TEXT_GENERATE",
                    "config": {
                        "model": "gpt-4o-mini",
                        "prompt": "Summarize this Slack message in one concise sentence: {{text}}",
                        "temperature": 0.2,
                        "max_tokens": 250
                    }
                },
                {
                    "type": "SLACK_SEND_MESSAGE",
                    "config": {
                        "channel": "{{channel_id}}",
                        "message": "AI Summary:\n{{ai_output}}"
                    }
                }
            ]
        }
    },
    {
        "name": "AI Support Reply Draft",
        "is_featured": True,
        "is_new": True,
        "install_count": 0,
        "difficulty": "Beginner",
        "estimated_setup_minutes": 7,
        "tags": ['ai', 'support', 'customer-service'],
        "description": "Generate a helpful support reply from a webhook support request.",
        "category": "AI Automation",
        "definition": {
            "trigger": {
                "type": "WEBHOOK_RECEIVED",
                "config": {}
            },
            "actions": [
                {
                    "type": "OPENAI_TEXT_GENERATE",
                    "config": {
                        "model": "gpt-4o-mini",
                        "prompt": "Write a helpful, polite support reply for this customer request. Customer: {{name}} Email: {{email}} Issue: {{message}}",
                        "temperature": 0.3,
                        "max_tokens": 600
                    }
                },
                {
                    "type": "ADD_AUDIT_LOG",
                    "config": {
                        "action": "AI Support Reply Draft: {{ai_output}}"
                    }
                }
            ]
        }
    },
    {
        "name": "AI Follow-up Message",
        "is_featured": True,
        "is_new": True,
        "install_count": 0,
        "difficulty": "Beginner",
        "estimated_setup_minutes": 6,
        "tags": ['ai', 'follow-up', 'sales'],
        "description": "Generate a short personalized follow-up message for a new lead.",
        "category": "AI Automation",
        "definition": {
            "trigger": {
                "type": "NEW_LEAD",
                "config": {}
            },
            "actions": [
                {
                    "type": "OPENAI_TEXT_GENERATE",
                    "config": {
                        "model": "gpt-4o-mini",
                        "prompt": "Write a short personalized follow-up message for this lead. Name: {{name}} Email: {{email}} Source: {{source}}",
                        "temperature": 0.4,
                        "max_tokens": 350
                    }
                },
                {
                    "type": "ADD_AUDIT_LOG",
                    "config": {
                        "action": "AI Follow-up Message: {{ai_output}}"
                    }
                }
            ]
        }
    }
]

db = SessionLocal()

for item in templates:
    existing = db.query(WorkflowTemplate).filter(
        WorkflowTemplate.name == item["name"]
    ).first()

    if existing:
        existing.description = item["description"]
        existing.category = item["category"]
        existing.definition = item["definition"]
        existing.is_active = True
        existing.is_featured = item.get("is_featured", False)
        existing.is_new = item.get("is_new", True)
        existing.difficulty = item.get("difficulty", "Beginner")
        existing.estimated_setup_minutes = item.get(
            "estimated_setup_minutes",
            5,
        )
        existing.tags = item.get("tags", [])
    else:
        db.add(
            WorkflowTemplate(
                name=item["name"],
                description=item["description"],
                category=item["category"],
                definition=item["definition"],
                is_active=True,
                is_featured=item.get("is_featured", False),
                is_new=item.get("is_new", True),
                install_count=0,
                difficulty=item.get("difficulty", "Beginner"),
                estimated_setup_minutes=item.get(
                    "estimated_setup_minutes",
                    5,
                ),
                tags=item.get("tags", []),
            )
        )

db.commit()
db.close()

print("Default workflow templates seeded successfully.")
