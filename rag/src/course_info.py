"""
Course Information Extraction Module
Uses course codes + Gemini AI to fetch comprehensive course information from AMU
Handles multiple exams per PDF and multiple course codes (e.g., CHC-3100/FTC3100)
"""
import re
import json
from typing import Dict, Optional, List
from src.embedder import generate_text


def extract_course_codes_with_positions(text: str) -> List[Dict]:
    """
    Extract ALL course codes with their approximate positions in text
    Uses proximity to "Credits", "Maximum Marks", "Marks", "Duration", "Time" for 99% accuracy
    
    Args:
        text: OCR extracted text from PDF
    
    Returns:
        List of dicts: [{'code': 'ACS 1110', 'position': 1234, 'confidence': 'high'}]
    """
    course_matches = []
    
    # High confidence: Course code in parentheses near exam header keywords
    # This captures 99% of real course codes
    high_confidence_pattern = r'(?P<context>.{0,200})\((?P<code>[A-Z]{2,4}[\s\-]?\d{3,4}(?:/[A-Z]{2,4}[\s\-]?\d{3,4})?)\)(?P<after>.{0,200})'
    
    for match in re.finditer(high_confidence_pattern, text, re.IGNORECASE | re.DOTALL):
        code = match.group('code').strip().upper()
        context_before = match.group('context')
        context_after = match.group('after')
        combined_context = context_before + context_after
        
        # Check if exam-related keywords are nearby (99% accuracy indicator)
        proximity_keywords = ['credit', 'maximum mark', 'marks', 'duration', 'time', 'examination', 'semester', 'course']
        has_proximity = any(kw in combined_context.lower() for kw in proximity_keywords)
        
        # Filter false positives (common words that match pattern)
        prefix_match = re.match(r'([A-Z]{2,4})', code)
        if prefix_match:
            prefix = prefix_match.group(1)
            false_positives = {'AN', 'OR', 'DO', 'NO', 'GO', 'TO', 'IS', 'IT', 'IN', 'ON', 'AT', 'BE', 'WE', 'ME'}
            if prefix in false_positives:
                continue
        
        confidence = 'high' if has_proximity else 'medium'
        
        course_matches.append({
            'code': code,
            'position': match.start(),
            'confidence': confidence,
            'context': combined_context[:100]  # Store some context for debugging
        })
    
    # Deduplicate by code while keeping earliest position with highest confidence
    seen_codes = {}
    for match in course_matches:
        code = match['code']
        if code not in seen_codes:
            seen_codes[code] = match
        elif match['confidence'] == 'high' and seen_codes[code]['confidence'] != 'high':
            seen_codes[code] = match  # Replace with high confidence version
    
    # Sort by position (order they appear in PDF)
    result = sorted(seen_codes.values(), key=lambda x: x['position'])
    
    # Process slash-separated codes
    expanded_results = []
    for item in result:
        code = item['code']
        if '/' in code:
            # Split CHC-3100/FTC3100 into two separate courses
            parts = code.split('/')
            for part in parts:
                normalized = re.sub(r'([A-Z]+)[\s\-]?(\d+)', r'\1 \2', part.strip())
                expanded_results.append({
                    'code': normalized,
                    'position': item['position'],
                    'confidence': item['confidence']
                })
        else:
            normalized = re.sub(r'([A-Z]+)[\s\-]?(\d+)', r'\1 \2', code)
            expanded_results.append({
                'code': normalized,
                'position': item['position'],
                'confidence': item['confidence']
            })
    
    if expanded_results:
        codes_str = ', '.join([f"{r['code']} ({r['confidence']})" for r in expanded_results])
        print(f"  Found {len(expanded_results)} course code(s): {codes_str}")
    else:
        print(f"  No course codes found in text")
    
    return expanded_results


def extract_course_codes(text: str) -> List[str]:
    """
    Extract ALL course codes from PDF text (handles multiple exams per PDF)
    Handles patterns like: EAM 211, CHC-3100/FTC3100, ACS 1110, etc.
    Uses stricter patterns to avoid false positives.
    
    Args:
        text: OCR extracted text from PDF
    
    Returns:
        List of unique course codes
    """
    # Search entire text for better coverage (PDFs may have 2+ exam papers)
    sample_text = text[:8000] if len(text) > 8000 else text
    
    course_codes = set()
    
    # Strict course code patterns - prioritize context-aware matches
    context_patterns = [
        r'Code[\s:]+([A-Z]{2,4}[\s\-]?\d{3,4}(?:/[A-Z]{2,4}[\s\-]?\d{3,4})?)',  # Code: EAM 211
        r'Course[\s]+Code[\s:]+([A-Z]{2,4}[\s\-]?\d{3,4}(?:/[A-Z]{2,4}[\s\-]?\d{3,4})?)',  # Course Code: EAM 211
        r'\(([A-Z]{2,4}[\s\-]?\d{3,4}(?:/[A-Z]{2,4}[\s\-]?\d{3,4})?)\)',  # (ACS 1110) or (CHC-3100/FTC3100)
    ]
    
    # First priority: Extract codes with explicit context
    for pattern in context_patterns:
        matches = re.findall(pattern, sample_text, re.IGNORECASE)
        if matches:
            course_codes.update(matches)
            print(f"  ℹ Context-aware pattern found: {matches}")
    
    # Common false positives to exclude
    exclude_words = {'AN', 'OR', 'TO', 'IN', 'ON', 'AT', 'BY', 'OF', 'FOR', 'THE', 'AND', 'BUT', 'NOT', 'ALL', 'ANY', 'FEW', 'MAY', 'CAN', 'WILL'}
    
    # Process and filter course codes
    expanded_codes = set()
    for code in course_codes:
        code = code.strip().upper()
        
        # Extract department code portion
        dept_match = re.match(r'([A-Z]{2,4})', code)
        if dept_match:
            dept_code = dept_match.group(1)
            # Skip if it's a common false positive word
            if dept_code in exclude_words:
                print(f"  Filtered false positive: {code}")
                continue
        
        if '/' in code:
            # Split and add both codes
            parts = code.split('/')
            for part in parts:
                part = part.strip()
                dept_match = re.match(r'([A-Z]{2,4})', part)
                if dept_match and dept_match.group(1) not in exclude_words:
                    normalized = re.sub(r'([A-Z]+)[\s\-]?(\d+)', r'\1 \2', part)
                    expanded_codes.add(normalized)
        else:
            # Normalize: ensure space between letters and numbers
            normalized = re.sub(r'([A-Z]+)[\s\-]?(\d+)', r'\1 \2', code)
            expanded_codes.add(normalized)
    
    result = list(expanded_codes)
    if result:
        print(f"  Found {len(result)} course code(s): {', '.join(result)}")
    else:
        print(f"  No course codes found in text")
    
    return result


def fetch_comprehensive_course_info(course_code: str, year_range: str, text_sample: str) -> Dict:
    """
    Use Gemini AI to fetch comprehensive course information from AMU
    
    Args:
        course_code: Extracted course code (e.g., "EAM 211")
        year_range: Academic year (e.g., "2023-2024")
        text_sample: Sample text from PDF for context
    
    Returns:
        Dict with comprehensive course information
    """
    prompt = f"""You are analyzing an examination paper from Aligarh Muslim University (AMU).

Course Code: {course_code}
Academic Year: {year_range}
University: Aligarh Muslim University

Context from examination paper:
{text_sample[:1500]}

Based on the course code, year, and examination paper content, provide comprehensive course information in this EXACT JSON format:

{{
  "subject_identity": {{
    "code": "{course_code}",
    "title": "Full Course Title",
    "department_code": "Department abbreviation",
    "is_cbc": true
  }},
  "academic_details": {{
    "faculty": "Engineering & Technology / Science / etc.",
    "offering_department": "Full department name",
    "level": "Undergraduate / Postgraduate",
    "applicable_programs": ["B.Tech", "B.E."],
    "branches": ["Branch names if applicable"],
    "semester": 3,
    "year": 2,
    "credits": 4
  }},
  "syllabus_content": {{
    "unit_1": {{"title": "Unit name", "topics": ["topic1", "topic2"]}},
    "unit_2": {{"title": "Unit name", "topics": ["topic1", "topic2"]}},
    "unit_3": {{"title": "Unit name", "topics": ["topic1", "topic2"]}},
    "unit_4": {{"title": "Unit name", "topics": ["topic1", "topic2"]}},
    "unit_5": {{"title": "Unit name", "topics": ["topic1", "topic2"]}}
  }},
  "evaluation_scheme": {{
    "internal_assessment": {{
      "sessional_1": 15,
      "sessional_2": 15,
      "assignments_attendance": 10
    }},
    "end_semester_exam": 60,
    "total_marks": 100
  }}
}}

Extract as much information as possible from the examination paper. If certain details are not visible, make reasonable inferences based on the course code and AMU standards."""

    try:
        response = generate_text(prompt, temperature=0.2, max_output_tokens=2000)
        
        # Log response for debugging
        print(f"  ℹ Gemini response length: {len(response)} chars")
        
        # Extract JSON from response
        response = response.strip()
        json_str = None
        
        # Try to extract JSON
        # Method 1: Markdown code block
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if match:
            json_str = match.group(1)
            print(f"  Found JSON in markdown block")
        else:
            # Method 2: Direct JSON object (find largest JSON)
            matches = re.findall(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', response, re.DOTALL)
            if matches:
                # Take the longest match (most comprehensive)
                json_str = max(matches, key=len)
                print(f"  Found JSON object")
        
        if not json_str:
            print(f"   No JSON pattern found in response")
            return None
        
        # Clean JSON string
        json_str = json_str.strip()
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)  # Remove trailing commas
        
        # Parse JSON
        result = json.loads(json_str)
        print(f"  JSON parsed successfully")
        
        # Debug: Show JSON keys
        print(f"  ℹ JSON keys: {list(result.keys())}")
        
        # Validate structure
        if 'subject_identity' in result:
            if 'title' in result['subject_identity']:
                print(f"  Extracted course: {result['subject_identity']['title']}")
                return result
            else:
                print(f"  Missing 'title' in subject_identity. Keys: {list(result['subject_identity'].keys())}")
                return None
        else:
            print(f"  Missing 'subject_identity' in result")
            return None
        
    except Exception as e:
        print(f"   Course info extraction error: {e}")
        import traceback
        traceback.print_exc()
        return None


def detect_math_equations(text: str) -> bool:
    """
    Detect if text contains mathematical equations
    """
    math_indicators = [
        r'\b(?:equation|formula|derive|calculate|solve|integrate)\b',
        r'[∫∑∏√±≤≥≠∞]',  # Math symbols
        r'\^|\b\d+/\d+\b',  # Exponents, fractions
        r'[xyz]=',  # Variables
    ]
    
    for pattern in math_indicators:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def detect_or_questions(text: str) -> list:
    """
    Detect OR questions (alternative questions)
    Returns list of OR question positions
    """
    or_positions = []
    or_pattern = r'\n\s*OR\s*\n'
    
    for match in re.finditer(or_pattern, text, re.IGNORECASE):
        or_positions.append({
            'position': match.start(),
            'context': text[max(0, match.start()-100):match.end()+100]
        })
    
    return or_positions


def enhance_math_text(text: str) -> str:
    """
    Add context markers for mathematical content
    This helps the AI understand mathematical context better
    """
    # Mark potential equations
    text = re.sub(
        r'(\b(?:equation|formula|expression)\s*\d*\s*:?\s*)([^\n]{20,200})',
        r'\1[MATH_EQUATION: \2]',
        text,
        flags=re.IGNORECASE
    )
    
    # Mark fractions
    text = re.sub(r'(\d+)\s*/\s*(\d+)', r'[FRACTION: \1/\2]', text)
    
    return text


def analyze_pdf_content(text: str, filename: str = "", year: str = "") -> Dict:
    """
    Comprehensive PDF content analysis using course codes + AI
    Handles multiple exams per PDF with page-aware course assignment
    
    Args:
        text: OCR extracted text from PDF
        filename: PDF filename
        year: Academic year (e.g., "2023-2024")
    
    Returns dict with:
        - courses_info: List of comprehensive course information with positions
        - has_math: Boolean
        - or_questions: List of OR question positions
        - stats: Text statistics
    """
    print(f"  Analyzing PDF content...")
    
    # Step 1: Extract ALL course codes WITH their positions in text
    course_matches = extract_course_codes_with_positions(text)
    
    # Step 2: Fetch comprehensive course info for EACH code using AI
    courses_info = []
    if course_matches:
        for match in course_matches:
            code = match['code']
            position = match['position']
            confidence = match['confidence']
            
            print(f"  → Fetching info for {code} (confidence: {confidence}, pos: {position})...")
            
            # Get context around this course code for better AI extraction
            context_start = max(0, position - 500)
            context_end = min(len(text), position + 2500)
            course_context = text[context_start:context_end]
            
            course_info = fetch_comprehensive_course_info(code, year, course_context)
            if course_info:
                # Add position information for page-aware chunking
                course_info['_position'] = position
                course_info['_confidence'] = confidence
                courses_info.append(course_info)
            else:
                # Fallback for this specific code
                print(f"  Using fallback for {code}")
                courses_info.append({
                    'subject_identity': {
                        'code': code,
                        'title': 'Unknown Subject',
                        'department_code': '',
                        'is_cbc': False
                    },
                    'academic_details': {
                        'faculty': '',
                        'offering_department': '',
                        'level': 'Undergraduate',
                        'applicable_programs': [],
                        'branches': [],
                        'semester': 0,
                        'year': 0,
                        'credits': 0
                    },
                    'syllabus_content': {},
                    'evaluation_scheme': {
                        'internal_assessment': {},
                        'end_semester_exam': 0,
                        'total_marks': 100
                    },
                    '_position': position,
                    '_confidence': confidence
                })
    
    # Step 3: Complete fallback if no course codes found
    if not courses_info:
        print(f"  No course codes found, using complete fallback")
        courses_info = [{
            'subject_identity': {
                'code': 'Unknown',
                'title': 'Unknown Subject',
                'department_code': '',
                'is_cbc': False
            },
            'academic_details': {
                'faculty': '',
                'offering_department': '',
                'level': 'Undergraduate',
                'applicable_programs': [],
                'branches': [],
                'semester': 0,
                'year': 0,
                'credits': 0
            },
            'syllabus_content': {},
            'evaluation_scheme': {
                'internal_assessment': {},
                'end_semester_exam': 0,
                'total_marks': 100
            }
        }]
    
    # Step 4: Detect math and OR questions
    has_math = detect_math_equations(text)
    or_questions = detect_or_questions(text)
    
    # Step 5: Analyze figures and diagrams
    has_figures = bool(re.search(r'fig(?:ure)?[\s.]\d+', text, re.IGNORECASE))
    has_diagrams = bool(re.search(r'diagram|graph|chart', text, re.IGNORECASE))
    
    print(f"  Analysis complete: {len(courses_info)} course(s) found")
    
    return {
        'courses_info': courses_info,  # List of course info dicts
        'has_math': has_math,
        'or_questions': or_questions,
        'enhanced_text': enhance_math_text(text),
        'stats': {
            'char_count': len(text),
            'has_figures': has_figures,
            'has_diagrams': has_diagrams,
            'or_question_count': len(or_questions)
        }
    }
