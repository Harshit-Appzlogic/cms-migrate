from typing import List, Dict, Any
from models import ComponentSchema, SchemaField, FIELD_TYPES


class SchemaCreator:
    """Creates clean CMS schemas from AI field definitions"""
    
    def create_schema(self, content_type: str, ai_fields: Dict[str, Dict]) -> ComponentSchema:
        """Create a schema from AI field definitions"""
        
        # Convert AI fields to our schema fields
        schema_fields = []
        for field_name, field_info in ai_fields.items():
            field = self._create_schema_field(field_name, field_info)
            schema_fields.append(field)
        
        # Create the complete schema
        return ComponentSchema(
            content_type=content_type,
            title=f"{content_type.title()} Content",
            fields=schema_fields,
            description=f"Schema for {content_type} content"
        )
    
    def _create_schema_field(self, field_name: str, field_info: Dict[str, Any]) -> SchemaField:
        """Create a schema field from AI field information"""
        return SchemaField(
            name=field_name,
            field_type=self._get_field_type(field_info.get('type', 'text')),
            display_name=self._make_display_name(field_name),
            required=field_info.get('required', False),
            multiline=field_info.get('multiline', False),
            options=field_info.get('enum_values')
        )
    
    def _get_field_type(self, ai_type: str) -> str:
        """Convert AI field type to our field type"""
        ai_type = ai_type.lower()
        
        # Map AI types to our supported types
        if ai_type in FIELD_TYPES:
            return ai_type
        
        # Default to text if we don't recognize it
        return 'text'
    
    def _make_display_name(self, field_name: str) -> str:
        """Make a nice display name from a field name"""
        # Convert snake_case to Title Case
        words = field_name.replace('_', ' ').split()
        return ' '.join(word.capitalize() for word in words)


class SchemaValidator:
    """Makes sure our schemas are valid"""
    
    def validate_schema(self, schema: ComponentSchema) -> bool:
        """Check if a schema is valid"""
        # Need at least one field
        if not schema.fields:
            return False
        
        # Need a title field (CMS requirement)
        field_names = [f.name for f in schema.fields]
        if 'title' not in field_names:
            return False
        
        # Check field names are valid
        for field in schema.fields:
            if not self._is_valid_field_name(field.name):
                return False
        
        return True
    
    def _is_valid_field_name(self, name: str) -> bool:
        """Check if a field name is valid"""
        # Must start with letter, only contain letters, numbers, underscores
        import re
        return bool(re.match(r'^[a-z][a-z0-9_]*$', name))


class SchemaEnhancer:
    """Adds useful fields to schemas"""
    
    def enhance_schema(self, schema: ComponentSchema) -> ComponentSchema:
        """Add common fields that are usually useful"""
        
        fields = list(schema.fields)
        
        # Add timestamp fields if missing
        if not self._has_field(fields, 'created_at'):
            fields.append(SchemaField(
                name='created_at',
                field_type='date',
                display_name='Created At',
                required=False
            ))
        
        if not self._has_field(fields, 'updated_at'):
            fields.append(SchemaField(
                name='updated_at',
                field_type='date',
                display_name='Updated At',
                required=False
            ))
        
        # Add content-specific fields
        fields = self._add_content_specific_fields(fields, schema.content_type)
        
        return ComponentSchema(
            content_type=schema.content_type,
            title=schema.title,
            fields=fields,
            description=schema.description
        )
    
    def _has_field(self, fields: List[SchemaField], field_name: str) -> bool:
        """Check if schema already has a field"""
        return any(f.name == field_name for f in fields)
    
    def _add_content_specific_fields(self, fields: List[SchemaField], content_type: str) -> List[SchemaField]:
        """Add fields specific to content type"""
        
        # Recipe-specific fields
        if content_type == 'recipe':
            if not self._has_field(fields, 'difficulty'):
                fields.append(SchemaField(
                    name='difficulty',
                    field_type='text',
                    display_name='Difficulty',
                    required=False,
                    options=['easy', 'medium', 'hard']
                ))
        
        # Article-specific fields
        elif content_type == 'article':
            if not self._has_field(fields, 'author'):
                fields.append(SchemaField(
                    name='author',
                    field_type='text',
                    display_name='Author',
                    required=False
                ))
        
        return fields