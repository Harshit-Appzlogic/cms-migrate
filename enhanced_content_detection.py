"""
Enhanced content detection for better component diversity
"""
from bs4 import Tag, BeautifulSoup
import re
from typing import Dict, List, Tuple


class EnhancedContentDetector:
    """Detect specific content types with high precision"""
    
    def __init__(self):
        # Define content type signatures
        self.content_signatures = {
            'headline-component': {
                'selectors': ['h1', 'h2', '.headline', '[class*="title"]', 'header h1', 'header h2'],
                'text_patterns': [r'\b(headline|title|breaking|news)\b'],
                'min_words': 2,
                'max_words': 15,
                'required_fields': ['headline_text']
            },
            
            'teaser-component': {
                'selectors': ['.teaser', '[class*="teaser"]', '.preview', '[class*="preview"]'],
                'text_patterns': [r'\b(read more|continue|learn more|discover)\b'],
                'has_image': True,
                'has_link': True,
                'min_words': 20,
                'max_words': 100,
                'required_fields': ['title', 'description', 'image', 'link']
            },
            
            'banner-component': {
                'selectors': ['.banner', '[class*="banner"]', '.hero', '[class*="hero"]', '.promo', 
                            '.grocery-minibanner', '.mini-banner', '[class*="minibanner"]'],
                'text_patterns': [r'\b(special|offer|limited|exclusive|promotion|delivery fee|add.*more)\b'],
                'has_image': False,  # These banners might not have images
                'prominent_text': True,
                'required_fields': ['title', 'call_to_action']
            },
            
            'article-component': {
                'selectors': ['article', '.article', '[class*="story"]', '.content'],
                'text_patterns': [r'\b(published|author|by|date|article)\b'],
                'min_words': 100,
                'has_headings': True,
                'has_paragraphs': True,
                'required_fields': ['title', 'content', 'author', 'publish_date']
            },
            
            'recipe-component': {
                'selectors': ['.recipe', '[class*="recipe"]', '[data-recipe]'],
                'text_patterns': [r'\b(ingredients|prep time|cook time|serves|recipe)\b'],
                'has_list': True,
                'min_words': 50,
                'required_fields': ['title', 'ingredients', 'prep_time', 'instructions']
            },
            
            'gallery-component': {
                'selectors': ['.gallery', '[class*="gallery"]', '.carousel', '.slideshow'],
                'min_images': 3,
                'has_navigation': True,
                'required_fields': ['images', 'captions']
            },
            
            'card-component': {
                'selectors': ['.card', '[class*="card"]', '.tile', '[class*="tile"]', 
                            '.offer-tile', '[class*="offer"]'],
                'has_image': True,
                'has_title': True,
                'compact_layout': True,
                'required_fields': ['title', 'image', 'description']
            },
            
            'promotional-tile': {
                'selectors': ['.offer-tile', '[class*="offer"]', '[data-bi-placement]'],
                'text_patterns': [r'\b(offer|special|deal|promotion|save|discount)\b'],
                'has_background_image': True,
                'promotional_content': True,
                'required_fields': ['title', 'image', 'offer_text']
            },
            
            'quote-component': {
                'selectors': ['blockquote', '.quote', '[class*="quote"]', '.testimonial'],
                'text_patterns': [r'["""].*["""]', r'\b(said|says|quote|testimonial)\b'],
                'required_fields': ['quote_text', 'author']
            },
            
            'list-component': {
                'selectors': ['ul', 'ol', '.list', '[class*="list"]'],
                'min_items': 3,
                'list_structure': True,
                'required_fields': ['items']
            },
            
            'form-component': {
                'selectors': ['form', '.form', '[class*="form"]', 'form[class*="Search"]'],
                'has_inputs': True,
                'has_submit': True,
                'required_fields': ['fields', 'action', 'method']
            },
            
            'membership-info': {
                'selectors': ['[id*="warehouse"]', '[class*="warehouse"]', '[class*="member"]'],
                'text_patterns': [r'\b(member|membership|executive|gold star|warehouse|hours)\b'],
                'min_words': 10,
                'required_fields': ['location', 'hours', 'member_type']
            },
            
            'costco-navbar': {
                'selectors': ['.costco-navbar', '.navbar', 'nav[class*="costco"]'],
                'text_patterns': [r'\b(costco|next|supplies|treasure|favorites)\b'],
                'has_navigation': True,
                'required_fields': ['navigation_items', 'brand']
            }
        }
    
    def detect_content_type(self, section: Tag) -> Tuple[str, float, Dict]:
        """Detect specific content type with confidence and extracted fields"""
        
        best_match = None
        best_score = 0.0
        best_fields = {}
        
        for content_type, signature in self.content_signatures.items():
            score, fields = self._match_signature(section, signature)
            if score > best_score and score > 0.4:  # Lowered confidence threshold
                best_match = content_type
                best_score = score
                best_fields = fields
        
        return best_match or 'generic-content', best_score, best_fields
    
    def _match_signature(self, section: Tag, signature: Dict) -> Tuple[float, Dict]:
        """Match section against content signature"""
        
        score = 0.0
        fields = {}
        
        # Check selector matches
        if 'selectors' in signature:
            selector_matches = any(
                self._element_matches_selector(section, selector)
                for selector in signature['selectors']
            )
            if selector_matches:
                score += 0.3
        
        # Check text patterns
        if 'text_patterns' in signature:
            text = section.get_text().lower()
            pattern_matches = sum(
                1 for pattern in signature['text_patterns']
                if re.search(pattern, text, re.IGNORECASE)
            )
            if pattern_matches > 0:
                score += 0.2 * min(pattern_matches, 2)  # Cap at 0.4
        
        # Check word count
        word_count = len(section.get_text().split())
        if 'min_words' in signature and word_count >= signature['min_words']:
            score += 0.1
        if 'max_words' in signature and word_count <= signature['max_words']:
            score += 0.1
        
        # Check structural requirements
        if signature.get('has_image') and section.find('img'):
            score += 0.2
            fields['image'] = section.find('img').get('src', '')
        
        # Check for background images in style attribute
        if signature.get('has_background_image'):
            style = section.get('style', '')
            if 'background-image' in style:
                score += 0.2
                # Extract background image URL
                bg_match = re.search(r'url\([\'"]?([^\'")]+)[\'"]?\)', style)
                if bg_match:
                    fields['background_image'] = bg_match.group(1)
        
        if signature.get('has_link') and section.find('a'):
            score += 0.1
            fields['link'] = section.find('a').get('href', '')
        
        if signature.get('has_headings') and section.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            score += 0.1
            heading = section.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            fields['title'] = heading.get_text(strip=True) if heading else ''
        
        if signature.get('has_paragraphs') and len(section.find_all('p')) >= 2:
            score += 0.1
            fields['content'] = ' '.join(p.get_text(strip=True) for p in section.find_all('p')[:3])
        
        if signature.get('has_list') and section.find(['ul', 'ol']):
            score += 0.1
            list_items = [li.get_text(strip=True) for li in section.find_all('li')[:10]]
            fields['ingredients' if 'recipe' in str(signature) else 'items'] = list_items
        
        if signature.get('min_images') and len(section.find_all('img')) >= signature['min_images']:
            score += 0.2
            images = [img.get('src', '') for img in section.find_all('img')[:5]]
            fields['images'] = images
        
        if signature.get('has_inputs') and section.find(['input', 'select', 'textarea']):
            score += 0.2
            form_fields = []
            for input_elem in section.find_all(['input', 'select', 'textarea']):
                form_fields.append({
                    'type': input_elem.get('type', input_elem.name),
                    'name': input_elem.get('name', ''),
                    'placeholder': input_elem.get('placeholder', '')
                })
            fields['fields'] = form_fields
        
        # Extract common fields
        if not fields.get('title') and section.find(['h1', 'h2', 'h3']):
            fields['title'] = section.find(['h1', 'h2', 'h3']).get_text(strip=True)
        
        if not fields.get('description'):
            # Get first meaningful paragraph or text
            if section.find('p'):
                fields['description'] = section.find('p').get_text(strip=True)[:200]
            else:
                fields['description'] = section.get_text(strip=True)[:200]
        
        return min(score, 1.0), fields
    
    def _element_matches_selector(self, element: Tag, selector: str) -> bool:
        """Check if element matches CSS selector"""
        try:
            # Handle simple cases
            if selector == element.name:
                return True
            
            # For class selectors like .navbar
            if selector.startswith('.'):
                class_name = selector[1:]
                element_classes = element.get('class', [])
                return class_name in element_classes
            
            # For ID selectors like #myid
            if selector.startswith('#'):
                id_name = selector[1:]
                return element.get('id') == id_name
            
            # For attribute selectors like [class*="banner"]
            if '[' in selector and ']' in selector:
                if 'class*=' in selector:
                    # Extract the class pattern
                    import re
                    match = re.search(r'class\*="([^"]*)"', selector)
                    if match:
                        pattern = match.group(1)
                        element_classes = element.get('class', [])
                        return any(pattern in cls for cls in element_classes)
                
                if 'id*=' in selector:
                    # Extract the id pattern
                    import re
                    match = re.search(r'id\*="([^"]*)"', selector)
                    if match:
                        pattern = match.group(1)
                        element_id = element.get('id', '')
                        return pattern in element_id
            
            # Fallback: create a temporary soup and check
            from bs4 import BeautifulSoup
            temp_soup = BeautifulSoup(str(element), 'html.parser')
            matches = temp_soup.select(selector)
            return len(matches) > 0 and matches[0] == element
            
        except Exception:
            return False


def create_enhanced_ai_prompt(section: Tag, content_type_hint: str, confidence: float, pre_extracted_fields: Dict, known_types: list) -> str:
    
    return f"""###Instruction###
You are an expert content analyst specializing in CMS component identification. Based on preliminary analysis, this content appears to be a {content_type_hint} (confidence: {confidence:.2f}).

I'm going to tip $300 for precise component classification!

###Pre-Analysis Results###
Detected Type: {content_type_hint}
Confidence: {confidence:.2f}
Pre-extracted Fields: {pre_extracted_fields}

###HTML Section###
{str(section)[:800]}

###Content Text###
{section.get_text(strip=True)[:400]}

###Task###
Refine the content type classification and enhance field extraction. Consider these specific component types:

**High Priority Types** (we need more of these):
- headline-component: Simple text headlines with styling options
- teaser-component: Preview cards with image, title, description, and link
- banner-component: Promotional banners with call-to-action
- article-component: Full articles with author, date, content
- card-component: Compact info cards with image and text
- quote-component: Testimonials or quotes with attribution
- gallery-component: Image galleries or carousels
- list-component: Structured lists of items

**Current Types**: {', '.join(known_types)}

###Requirements###
1. If the pre-analysis suggests a specific component type, validate and refine it
2. Extract ALL relevant fields for that component type
3. If you disagree with the pre-analysis, suggest a better type with reasoning
4. Focus on creating reusable, structured components

Return JSON:
{{
  "type": "specific-component-type",
  "confidence": 0.95,
  "reasoning": "Why this classification is correct",
  "fields": {{
    "field1": "extracted_value",
    "field2": ["array", "of", "values"]
  }}
}}"""


def get_content_type_examples() -> Dict[str, str]:
    """Provide examples of each content type for AI training"""
    
    return {
        'headline-component': 'Simple text headlines like "Breaking News" or "Welcome Message"',
        'teaser-component': 'Preview cards with image, title, short description, and "Read More" link',
        'banner-component': 'Promotional sections with large images and call-to-action buttons',
        'article-component': 'Full content pieces with headlines, author, publish date, and body text',
        'card-component': 'Compact information cards with image, title, and brief description',
        'quote-component': 'Customer testimonials, reviews, or quoted text with author attribution',
        'gallery-component': 'Image galleries, photo carousels, or media showcases',
        'list-component': 'Structured lists like features, benefits, or menu items'
    }