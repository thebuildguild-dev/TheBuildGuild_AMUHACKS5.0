"""
PDF Parser Module
Extracts text from PDF files using pdfminer.six with OCR fallback
"""
import os
from pathlib import Path
from typing import Generator, List
from io import StringIO

from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.pdfpage import PDFPage

# OCR imports - optional dependencies
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("OCR dependencies not available. Install pdf2image and pytesseract for image-based PDF support.")


def extract_text_from_pdf(pdf_path: str, max_pages: int = None) -> str:
    """
    Extract text from a PDF file using pdfminer.six with OCR fallback
    
    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to extract (None for all)
    
    Returns:
        Extracted text as string
    
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        Exception: If extraction fails
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    try:
        # Primary method: High-level extraction (faster)
        text = extract_text(pdf_path, maxpages=max_pages)
        
        if text and text.strip():
            print(f"Extracted {len(text)} characters from {os.path.basename(pdf_path)}")
            return text.strip()
        
        # Fallback 1: Low-level extraction with custom parameters
        print(f"Primary extraction returned empty, trying fallback for {os.path.basename(pdf_path)}")
        text = extract_text_fallback(pdf_path, max_pages)
        
        if text and text.strip():
            print(f"Fallback extracted {len(text)} characters")
            return text.strip()
        
        # Fallback 2: OCR for image-based PDFs
        if OCR_AVAILABLE:
            print(f"No text layer found, trying OCR for {os.path.basename(pdf_path)}")
            text = extract_text_with_ocr(pdf_path, max_pages)
            
            if text and text.strip():
                print(f"OCR extracted {len(text)} characters")
                return text.strip()
        
        # Last resort: Return empty string with warning
        print(f"No text extracted from {os.path.basename(pdf_path)}")
        return ""
    
    except Exception as e:
        print(f" Error extracting text from {pdf_path}: {e}")
        # Try OCR as final fallback
        if OCR_AVAILABLE:
            try:
                return extract_text_with_ocr(pdf_path, max_pages)
            except:
                pass
        raise Exception(f"Failed to extract text from {pdf_path}: {e}")


def extract_text(pdf_path: str, maxpages: int = None) -> str:
    """
    Primary extraction method using pdfminer's high-level API
    
    Args:
        pdf_path: Path to PDF file
        maxpages: Maximum pages to extract
    
    Returns:
        Extracted text
    """
    output_string = StringIO()
    
    with open(pdf_path, 'rb') as pdf_file:
        extract_text_to_fp(
            pdf_file,
            output_string,
            maxpages=maxpages,
            laparams=LAParams(),
        )
    
    return output_string.getvalue()


def extract_text_fallback(pdf_path: str, max_pages: int = None) -> str:
    """
    Fallback extraction method with custom LAParams for better text extraction
    
    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum pages to extract
    
    Returns:
        Extracted text
    """
    output_string = StringIO()
    
    # Custom LAParams for better text extraction
    laparams = LAParams(
        line_overlap=0.5,
        char_margin=2.0,
        line_margin=0.5,
        word_margin=0.1,
        boxes_flow=0.5,
        detect_vertical=True,
        all_texts=False
    )
    
    with open(pdf_path, 'rb') as pdf_file:
        rsrcmgr = PDFResourceManager()
        device = TextConverter(rsrcmgr, output_string, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        
        page_count = 0
        for page in PDFPage.get_pages(pdf_file, check_extractable=True):
            if max_pages and page_count >= max_pages:
                break
            interpreter.process_page(page)
            page_count += 1
        
        device.close()
    
    return output_string.getvalue()


def extract_text_with_ocr(pdf_path: str, max_pages: int = None) -> str:
    """
    Extract text from image-based PDFs using OCR (Tesseract)
    
    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum pages to extract
    
    Returns:
        Extracted text from OCR
    """
    if not OCR_AVAILABLE:
        raise ImportError("OCR dependencies not installed. Install pdf2image and pytesseract.")
    
    try:
        # Convert PDF to images
        # Use lower DPI for faster processing (200 is good balance)
        images = convert_from_path(
            pdf_path,
            dpi=200,
            first_page=1,
            last_page=max_pages if max_pages else None,
            fmt='jpeg',
            thread_count=2
        )
        
        # Extract text from each image
        all_text = []
        for i, image in enumerate(images, 1):
            print(f"    → OCR processing page {i}/{len(images)}...")
            
            # Use pytesseract to extract text
            text = pytesseract.image_to_string(image, lang='eng')
            
            if text.strip():
                all_text.append(text.strip())
        
        return '\n\n'.join(all_text)
    
    except Exception as e:
        print(f"   OCR extraction failed: {e}")
        return ""


def list_pdfs_in_folder(folder_path: str, recursive: bool = False) -> Generator[str, None, None]:
    """
    List all PDF files in a folder
    
    Args:
        folder_path: Path to folder
        recursive: If True, search subdirectories
    
    Yields:
        Full paths to PDF files
    
    Raises:
        FileNotFoundError: If folder doesn't exist
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    if not os.path.isdir(folder_path):
        raise ValueError(f"Path is not a directory: {folder_path}")
    
    folder = Path(folder_path)
    
    if recursive:
        # Search recursively
        pattern = "**/*.pdf"
    else:
        # Search only in current directory
        pattern = "*.pdf"
    
    pdf_files = sorted(folder.glob(pattern))
    
    if not pdf_files:
        print(f"No PDF files found in {folder_path}")
    else:
        print(f"Found {len(pdf_files)} PDF file(s) in {folder_path}")
    
    for pdf_file in pdf_files:
        yield str(pdf_file.absolute())


def get_pdf_metadata(pdf_path: str) -> dict:
    """
    Extract basic metadata from a PDF file
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Dictionary with metadata (pages, size, etc.)
    """
    try:
        from pdfminer.pdfparser import PDFParser
        from pdfminer.pdfdocument import PDFDocument
        
        metadata = {
            "filename": os.path.basename(pdf_path),
            "size_bytes": os.path.getsize(pdf_path),
            "pages": 0,
        }
        
        with open(pdf_path, 'rb') as fp:
            parser = PDFParser(fp)
            document = PDFDocument(parser)
            
            # Count pages
            num_pages = sum(1 for _ in PDFPage.get_pages(fp))
            metadata["pages"] = num_pages
            
            # Extract document info if available
            if document.info:
                for info in document.info:
                    metadata.update({
                        key.decode() if isinstance(key, bytes) else key: 
                        value.decode() if isinstance(value, bytes) else value
                        for key, value in info.items()
                    })
        
        return metadata
    
    except Exception as e:
        print(f"Could not extract metadata from {pdf_path}: {e}")
        return {
            "filename": os.path.basename(pdf_path),
            "size_bytes": os.path.getsize(pdf_path),
            "pages": 0,
        }


def validate_pdf(pdf_path: str) -> bool:
    """
    Validate if a file is a readable PDF
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        True if valid PDF, False otherwise
    """
    try:
        with open(pdf_path, 'rb') as fp:
            # Check PDF header
            header = fp.read(5)
            if header != b'%PDF-':
                return False
            
            # Try to parse first page
            fp.seek(0)
            list(PDFPage.get_pages(fp, maxpages=1))
            return True
    
    except Exception:
        return False
