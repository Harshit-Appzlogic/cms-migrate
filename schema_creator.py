from models import ComponentSchema, SchemaField, FIELD_TYPES
import re


def create_schema(content_type: str, ai_fields: dict) -> ComponentSchema:
    """Create a schema from what the AI found"""
    
    # Turn AI fields into schema fields
    fields = []
    for name, info in ai_fields.items():
        field = SchemaField(
            name=name,
            field_type=info.get('type', 'text') if info.get('type') in FIELD_TYPES else 'text',
            display_name=name.replace('_', ' ').title(),
            required=info.get('required', False),
            multiline=info.get('multiline', False),
            options=info.get('enum_values')
        )
        fields.append(field)
    
    return ComponentSchema(
        content_type=content_type,
        title=f"{content_type.title()} Content",
        fields=fields,
        description=f"Schema for {content_type} content"
    )


def is_schema_good(schema: ComponentSchema) -> bool:
    """Check if the schema makes sense"""
    # Need some fields
    if not schema.fields:
        return False
    
    # Need at least 1 meaningful field
    if len(schema.fields) < 1:
        return False
    
    # Field names should be reasonable (allow more flexible naming)
    for field in schema.fields:
        # Allow letters, numbers, underscores, hyphens
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', field.name):
            return False
        
        # Field name shouldn't be too long
        if len(field.name) > 50:
            return False
    
    # Schema should have a title
    if not schema.title or len(schema.title.strip()) == 0:
        return False
    
    return True