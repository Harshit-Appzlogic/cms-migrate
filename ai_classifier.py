"""
AI classifier that figures out what type of content we're looking at
"""
import json
import re
import cohere
from bs4 import Tag

from models import ComponentResult, COMPONENT_TYPES


class AIClassifier:
    """Uses AI to figure out what type of content we're looking at"""
    
    def __init__(self, api_key: str):
        self.cohere = cohere.Client(api_key)
        self.component_types = COMPONENT_TYPES
    
    def classify_content(self, section: Tag, filename: str) -> ComponentResult:
        """Look at a section of HTML and figure out what type of content it is"""
        try:
            # Get the HTML and text in manageable chunks
            html_snippet = self._get_html_snippet(section)
            text_content = self._get_text_content(section)
            
            # Ask the AI what it thinks this is
            prompt = self._create_prompt(html_snippet, text_content)
            response = self._ask_ai(prompt)
            
            # Parse the AI's response
            result = self._parse_ai_response(response)
            
            if result:
                return ComponentResult(
                    content_type=result.get('type', 'unknown'),
                    confidence=result.get('confidence', 0.0),
                    fields=result.get('fields', {}),
                    source_file=filename,
                    html_content=html_snippet
                )
            
            # If we couldn't parse the response, return unknown
            return ComponentResult(
                content_type='unknown',
                confidence=0.0,
                fields={},
                source_file=filename,
                html_content=html_snippet
            )
            
        except Exception as e:
            print(f"AI classification failed for {filename}: {e}")
            return ComponentResult(
                content_type='unknown',
                confidence=0.0,
                fields={},
                source_file=filename,
                html_content=""
            )
    
    def _get_html_snippet(self, section: Tag) -> str:
        """Get a reasonable chunk of HTML to show the AI"""
        html_str = str(section)
        # Don't send too much - it's expensive and the AI doesn't need it all
        return html_str[:1500]
    
    def _get_text_content(self, section: Tag) -> str:
        """Get the text content in a reasonable chunk"""
        text = section.get_text(strip=True)
        return text[:800]
    
    def _create_prompt(self, html: str, text: str) -> str:
        """Create a prompt to ask the AI what this content is"""
        types_list = ', '.join(self.component_types)
        
        return f"""Look at this HTML section and tell me what type of content it is.

HTML:
{html}

Text content:
{text}

What type of content is this? Choose from: {types_list}

Also extract any key information you can find (like title, description, etc.).

Please respond with JSON like this:
{{
  "type": "recipe",
  "confidence": 0.85,
  "fields": {{
    "title": "Chocolate Cake Recipe",
    "description": "A delicious chocolate cake"
  }}
}}"""
    
    def _ask_ai(self, prompt: str) -> str:
        """Ask the AI and get its response"""
        response = self.cohere.chat(
            model="command-r-plus",
            message=prompt,
            max_tokens=800,
            temperature=0.1  # Keep it focused
        )
        return response.text.strip()
    
    def _parse_ai_response(self, response: str) -> dict:
        """Try to parse the AI's JSON response"""
        try:
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        return None


class SchemaGenerator:
    """Uses AI to generate schemas for content types"""
    
    def __init__(self, api_key: str):
        self.cohere = cohere.Client(api_key)
    
    def generate_schema(self, content_type: str, examples: list) -> dict:
        """Generate a schema for a content type based on examples"""
        try:
            # Collect sample data from examples
            sample_data = []
            for example in examples[:5]:  # Don't need too many examples
                if hasattr(example, 'fields'):
                    sample_data.append(example.fields)
                elif isinstance(example, dict) and 'fields' in example:
                    sample_data.append(example['fields'])
            
            # Ask the AI to create a schema
            prompt = self._create_schema_prompt(content_type, sample_data)
            response = self._ask_ai(prompt)
            
            # Parse the response
            return self._parse_schema_response(response)
            
        except Exception as e:
            print(f"Schema generation failed for {content_type}: {e}")
            return None
    
    def _create_schema_prompt(self, content_type: str, examples: list) -> str:
        """Create a prompt to generate a schema"""
        return f"""I need to create a schema for {content_type} content based on these examples:

Examples:
{json.dumps(examples, indent=2)}

Please create a comprehensive schema that includes:
- All the important fields found in the examples
- Appropriate field types (text, file, number, boolean, date)
- Which fields are required vs optional
- Which text fields should be multiline
- Any enum values for dropdown fields

Respond with JSON like this:
{{
  "fields": {{
    "title": {{
      "type": "text",
      "required": true,
      "multiline": false
    }},
    "description": {{
      "type": "text",
      "required": false,
      "multiline": true
    }}
  }}
}}"""
    
    def _ask_ai(self, prompt: str) -> str:
        """Ask the AI for a schema"""
        response = self.cohere.chat(
            model="command-r-plus",
            message=prompt,
            max_tokens=1000,
            temperature=0.1
        )
        return response.text.strip()
    
    def _parse_schema_response(self, response: str) -> dict:
        """Parse the AI's schema response"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        return None