import json
import re
# import cohere
from bs4 import Tag
# from google import genai
from openai import OpenAI

from models import ComponentResult, add_content_type, get_content_types
from smart_parser import extract_smart_content
from enhanced_content_detection import EnhancedContentDetector, create_enhanced_ai_prompt


class AIClassifier:
    """Uses AI to figure out what type of content we're looking at"""
    
    def __init__(self, api_key: str):
        # self.cohere = cohere.Client(api_key)
        self.client = OpenAI(api_key=api_key)
        self.page_context = None  # Store page context for better classification
        self.content_detector = EnhancedContentDetector()  # Enhanced content detection
    
    def classify_content(self, section: Tag, filename: str, html_file=None) -> ComponentResult:
        """Look at a section of HTML and figure out what type of content it is"""
        try:
            # Step 1: Enhanced content detection (pre-analysis)
            detected_type, confidence, pre_fields = self.content_detector.detect_content_type(section)
            
            # Step 2: Use smart parsing for structured data
            smart_data = extract_smart_content(section)
            
            # Step 3: Skip page context for now (removed dependency)
            
            # Step 4: Create enhanced AI prompt with pre-analysis
            prompt = create_enhanced_ai_prompt(section, detected_type, confidence, pre_fields, get_content_types())
            response = self._ask_ai(prompt)
            
            # Parse the AI's response
            result = self._parse_ai_response(response)
            
            if result:
                content_type = result.get('type', 'unknown')
                confidence = result.get('confidence', 0.0)
                
                # Learn new content types as we find them
                add_content_type(content_type)
                
                return ComponentResult(
                    content_type=content_type,
                    confidence=confidence,
                    fields=result.get('fields', {}),
                    source_file=filename,
                    html_content=smart_data['clean_html']
                )
            
            # If we couldn't parse the response, return unknown
            return ComponentResult(
                content_type='unknown',
                confidence=0.0,
                fields={},
                source_file=filename,
                html_content=smart_data.get('clean_html', '') if 'smart_data' in locals() else ""
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
    
    def _create_smart_prompt(self, smart_data: dict, filename: str) -> str:
        """Create a prompt using smart parsed data"""
        current_types = get_content_types()
        types_we_know = ', '.join(current_types)
        
        # Page context removed for now
        context_info = ""
        
        structured = smart_data['structured']
        
        return f"""###Instruction###
You are an expert HTML content classifier. Your task is to analyze structured web content and classify it precisely. You MUST extract specific field values, not generic text.

I'm going to tip $200 for a better solution!
{context_info}
###Structured Data###
Headings: {structured['headings'][:3]}  # First 3 headings
Links: {len(structured['links'])} links found - Sample: {[link['text'] for link in structured['links'][:5]]}
Images: {len(structured['images'])} images - Sample alt text: {[img['alt'] for img in structured['images'][:3]]}
Forms: {len(structured['forms'])} forms found
Lists: {len(structured['lists'])} list items - Sample: {structured['lists'][:3]}

###Clean HTML###
{smart_data['clean_html']}

###Semantic Text###
{smart_data['semantic_text']}

###Known Types###
{types_we_know}

###Requirements###
1. Classify into specific types: magazine-section, product-showcase, store-locator, membership-info, navigation-menu, search-form, content-article, recipe-card, etc.
2. Extract SPECIFIC values from the structured data above - use headings for titles, links for navigation, etc.
3. Use page context to inform classification

You MUST return valid JSON:
{{
  "type": "specific-content-type",
  "confidence": 0.9,
  "fields": {{
    "title": "actual title from headings",
    "links": ["actual link texts"],
    "description": "specific description found"
  }}
}}"""

    def _create_prompt(self, html: str, text: str) -> str:
        """Create a prompt to ask the AI what this content is"""
        current_types = get_content_types()
        types_we_know = ', '.join(current_types)
        
        return f"""###Instruction###
You are an expert HTML content classifier and data extractor. Your task is to analyze HTML content and extract specific structured data. You MUST classify content into precise types and extract exact field values. You will be penalized for generic classifications or returning full text instead of specific values.

I'm going to tip $200 for a better solution!

###Example###
HTML: <div class="product"><h2>iPhone 15 Pro</h2><p>$999</p><p>Latest smartphone</p></div>
Output: {{"type": "product", "confidence": 0.95, "fields": {{"title": "iPhone 15 Pro", "price": "$999", "description": "Latest smartphone"}}}}

HTML: <nav><a href="/home">Home</a><a href="/about">About</a></nav>
Output: {{"type": "navigation", "confidence": 0.9, "fields": {{"links": ["Home", "About"]}}}}

###Task###
Analyze this HTML content step by step:

=== HTML ===
{html}

=== Text ===
{text}

=== Previous Types ===
{types_we_know}

###Requirements###
1. Create specific content type names (product, hero-banner, testimonial, store-locator, membership-info, pricing-table, contact-form, etc.)
2. Extract SPECIFIC values for each field - not generic text
3. Confidence must reflect actual match quality
4. Field names must describe the actual content

You MUST return valid JSON with this exact structure:
{{
  "type": "specific-content-type",
  "confidence": 0.8,
  "fields": {{
    "field_name": "specific_extracted_value"
  }}
}}"""
    
    def _ask_ai(self, prompt: str) -> str:
        """Ask the AI and get its response"""
        # response = self.cohere.chat(
        #     model="command-r-plus-08-2024",
        #     message=prompt,
        #     max_tokens=800,
        #     temperature=0.1  # Keep it focused
        # )
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    
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
        # self.cohere = cohere.Client(api_key)
        self.client = OpenAI(api_key=api_key)
    
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
        return f"""###Instruction###
You are an expert CMS schema architect. Your task is to create comprehensive content schemas for {content_type} content. You MUST analyze field patterns and create optimal schema definitions. You will be penalized for missing important fields or incorrect field types.

I'm going to tip $150 for a better solution!

###Example###
Examples: [{{"title": "Product A", "price": "$99", "description": "Good product"}}]
Output: {{"fields": {{"title": {{"type": "text", "required": true, "multiline": false}}, "price": {{"type": "text", "required": true, "multiline": false}}, "description": {{"type": "text", "required": false, "multiline": true}}}}}}

###Task###
Analyze these {content_type} examples step by step:

=== Examples ===
{json.dumps(examples, indent=2)}

###Requirements###
1. Include ALL fields that appear in examples
2. Use correct field types: text, file, number, boolean, date
3. Mark frequently appearing fields as required
4. Set multiline=true for long descriptions
5. Identify enum values for consistent dropdown options

You MUST return valid JSON with this structure:
{{
  "fields": {{
    "field_name": {{
      "type": "text|file|number|boolean|date",
      "required": true|false,
      "multiline": true|false
    }}
  }}
}}"""
    
    def _ask_ai(self, prompt: str) -> str:
        """Ask the AI for a schema"""
        # response = self.cohere.chat(
        #     model="command-r-plus",
        #     message=prompt,
        #     max_tokens=1000,
        #     temperature=0.1
        # )

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()

    def _parse_schema_response(self, response: str) -> dict:
        """Parse the AI's schema response"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                return parsed
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Response was: {response[:200]}...")
        except Exception as e:
            print(f"Schema parsing error: {e}")
        
        print("⚠️ Failed to parse schema response, returning empty schema")
        return {"fields": {}}