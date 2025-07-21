"""
Intelligent HTML parsing that extracts maximum meaningful content
while keeping LLM context manageable
"""
from bs4 import BeautifulSoup, Tag
import re


def extract_smart_content(section: Tag) -> dict:
    """Extract content intelligently - keep important, remove noise"""
    
    # 1. Get structured data first
    structured_data = {}
    
    # Extract key elements
    structured_data['headings'] = [h.get_text(strip=True) for h in section.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
    structured_data['links'] = [{'text': a.get_text(strip=True), 'href': a.get('href', '')} for a in section.find_all('a') if a.get_text(strip=True)]
    structured_data['images'] = [{'alt': img.get('alt', ''), 'src': img.get('src', '')} for img in section.find_all('img')]
    structured_data['forms'] = extract_form_data(section)
    structured_data['lists'] = [li.get_text(strip=True) for ul in section.find_all(['ul', 'ol']) for li in ul.find_all('li')]
    
    # 2. Get clean HTML (remove noise)
    clean_html = get_clean_html(section)
    
    # 3. Get semantic text
    semantic_text = get_semantic_text(section)
    
    return {
        'structured': structured_data,
        'clean_html': clean_html[:1000],  # Reduced but cleaner
        'semantic_text': semantic_text[:600]  # Reduced but more meaningful
    }


def extract_form_data(section: Tag) -> list:
    """Extract form structure intelligently"""
    forms = []
    for form in section.find_all('form'):
        form_data = {
            'action': form.get('action', ''),
            'method': form.get('method', ''),
            'fields': []
        }
        
        # Get form fields
        for input_elem in form.find_all(['input', 'select', 'textarea']):
            field = {
                'type': input_elem.get('type', input_elem.name),
                'name': input_elem.get('name', ''),
                'id': input_elem.get('id', ''),
                'placeholder': input_elem.get('placeholder', ''),
                'required': input_elem.get('required') is not None
            }
            form_data['fields'].append(field)
        
        forms.append(form_data)
    
    return forms


def get_clean_html(section: Tag) -> str:
    """Get HTML with noise removed"""
    # Clone the section
    clean_section = BeautifulSoup(str(section), 'html.parser')
    
    # Remove noise elements
    noise_selectors = [
        'script', 'style', 'noscript', '.ads', '.advertisement', 
        '.social-media', '.cookie-banner', '.popup'
    ]
    
    for selector in noise_selectors:
        for elem in clean_section.select(selector):
            elem.decompose()
    
    # Remove excessive whitespace and attributes we don't need
    html_str = str(clean_section)
    
    # Clean up attributes - keep only important ones
    html_str = re.sub(r'\s+(class|id|href|src|alt|action|method|type|name)="([^"]*)"', r' \1="\2"', html_str)
    html_str = re.sub(r'\s+[a-zA-Z-]+="[^"]*"', '', html_str)  # Remove other attributes
    
    # Clean up whitespace
    html_str = re.sub(r'\s+', ' ', html_str)
    html_str = re.sub(r'>\s+<', '><', html_str)
    
    return html_str.strip()


def get_semantic_text(section: Tag) -> str:
    """Extract semantically important text"""
    important_text = []
    
    # Get text from important elements in order of importance
    for selector in ['h1', 'h2', 'h3', 'title', '.price', '.amount', '.total']:
        for elem in section.select(selector):
            text = elem.get_text(strip=True)
            if text and text not in important_text:
                important_text.append(f"[{selector.upper()}] {text}")
    
    # Get paragraph text
    for p in section.find_all('p'):
        text = p.get_text(strip=True)
        if len(text) > 20:  # Only meaningful paragraphs
            important_text.append(text)
    
    # Get list items
    for li in section.find_all('li'):
        text = li.get_text(strip=True)
        if len(text) > 10:  # Only meaningful list items
            important_text.append(f"• {text}")
    
    return ' | '.join(important_text)


def create_smart_prompt(content_data: dict, known_types: list) -> str:
    """Create an intelligent prompt with structured data"""
    
    structured = content_data['structured']
    
    return f"""###Instruction###
You are an expert HTML content classifier. Your task is to analyze structured web content and classify it precisely. You MUST extract specific field values, not generic text.

I'm going to tip $200 for a better solution!

###Structured Data###
Headings: {structured['headings']}
Links: {[link['text'] for link in structured['links'][:5]]}
Images: {len(structured['images'])} images found
Forms: {len(structured['forms'])} forms found
Lists: {structured['lists'][:3]} (showing first 3)

###Clean HTML###
{content_data['clean_html']}

###Semantic Text###
{content_data['semantic_text']}

###Known Types###
{', '.join(known_types)}

###Requirements###
1. Classify into specific types: product, hero-banner, testimonial, store-locator, membership-info, pricing-table, contact-form, search-box, etc.
2. Extract SPECIFIC values from the structured data above
3. Use headings, links, and form data to identify precise field values

You MUST return valid JSON:
{{
  "type": "specific-content-type",
  "confidence": 0.9,
  "fields": {{
    "title": "actual title from headings",
    "links": ["actual link texts"],
    "price": "actual price if found"
  }}
}}"""