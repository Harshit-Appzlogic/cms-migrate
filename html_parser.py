"""
Simple HTML parser that finds interesting content sections
"""
from typing import List
from pathlib import Path
import re

from bs4 import BeautifulSoup, Tag


class HTMLParser:
    """Finds interesting content in HTML files"""
    
    def __init__(self):
        # What HTML elements usually contain interesting content?
        self.content_selectors = [
            'article', 'section', 'main', 'div.content', 'div.recipe', 
            'div.article', 'div.teaser', 'div.banner', 'nav', 'form',
            'header', 'aside', '.component', '.widget'
        ]
        
        # Skip these - they're usually not content
        self.skip_patterns = [
            r'^\s*menu\s*$', r'^\s*navigation\s*$', r'^\s*footer\s*$',
            r'^\s*header\s*$', r'^\s*copyright\s*$', r'^\s*login\s*$'
        ]
    
    def find_content_sections(self, html_file: Path) -> List[Tag]:
        """Find all the interesting content sections in an HTML file"""
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            sections = []
            
            # Try our known selectors first
            for selector in self.content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    if self._looks_like_content(element):
                        sections.append(element)
            
            # If we didn't find much, try looking at divs
            if len(sections) < 3:
                for div in soup.find_all('div'):
                    if self._looks_like_content(div):
                        sections.append(div)
            
            # Don't return too many - it gets overwhelming
            return sections[:15]
            
        except Exception as e:
            print(f"Couldn't read {html_file}: {e}")
            return []
    
    def _looks_like_content(self, element: Tag) -> bool:
        """Does this element look like it contains real content?"""
        text = element.get_text(strip=True)
        
        # Too short or too long probably isn't useful
        if len(text) < 50 or len(text) > 3000:
            return False
        
        # Need enough words to be meaningful
        words = text.split()
        if len(words) < 10:
            return False
        
        # Skip obvious navigation/footer stuff
        text_lower = text.lower()
        for pattern in self.skip_patterns:
            if re.match(pattern, text_lower):
                return False
        
        return True


class ContentExtractor:
    """Extracts specific types of content from HTML sections"""
    
    def get_title(self, section: Tag) -> str:
        """Try to find a title in this section"""
        # Look for heading tags first
        for heading in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            element = section.find(heading)
            if element:
                return element.get_text(strip=True)
        
        # Look for things that look like titles
        for selector in ['.title', '.heading', '.recipe-title', '[class*="title"]']:
            element = section.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # Give up - no title found
        return ""
    
    def get_description(self, section: Tag) -> str:
        """Try to find a description or main content"""
        # Look for paragraphs
        paragraphs = section.find_all('p')
        if paragraphs:
            return ' '.join([p.get_text(strip=True) for p in paragraphs])
        
        # Look for description-like classes
        for selector in ['.description', '.content', '.summary', '[class*="desc"]']:
            element = section.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # Just return the text we have
        return section.get_text(strip=True)[:500]
    
    def get_image_url(self, section: Tag) -> str:
        """Try to find an image in this section"""
        img = section.find('img')
        if img and img.get('src'):
            return img.get('src')
        return ""
    
    def get_link_url(self, section: Tag) -> str:
        """Try to find a link in this section"""
        link = section.find('a')
        if link and link.get('href'):
            return link.get('href')
        return ""
    
    def get_ingredients(self, section: Tag) -> List[str]:
        """Try to find ingredients (for recipes)"""
        ingredients = []
        
        # Look for lists that might be ingredients
        for list_element in section.find_all(['ul', 'ol']):
            if self._looks_like_ingredients(list_element):
                for item in list_element.find_all('li'):
                    ingredients.append(item.get_text(strip=True))
        
        return ingredients
    
    def _looks_like_ingredients(self, list_element: Tag) -> bool:
        """Does this list look like it contains ingredients?"""
        text = list_element.get_text().lower()
        # Look for cooking-related words
        cooking_words = ['cup', 'tbsp', 'tsp', 'oz', 'lb', 'gram', 'kg', 'ml', 'liter']
        return any(word in text for word in cooking_words)
    
    def get_field_value(self, section: Tag, field_name: str) -> str:
        """Try to extract a specific field from this section"""
        field_name = field_name.lower()
        
        # Map field names to extraction methods
        if field_name in ['title', 'heading', 'name']:
            return self.get_title(section)
        elif field_name in ['description', 'content', 'body', 'text']:
            return self.get_description(section)
        elif field_name in ['image', 'img', 'photo']:
            return self.get_image_url(section)
        elif field_name in ['link', 'url', 'href']:
            return self.get_link_url(section)
        elif field_name == 'ingredients':
            ingredients = self.get_ingredients(section)
            return '\n'.join(ingredients) if ingredients else ""
        else:
            # Default: just return some text
            return section.get_text(strip=True)[:200]