"""
Document Classifier Module

Uses LLM to classify documents instead of hardcoded keyword arrays.
Provides intelligent document analysis and data extraction.
"""

import os
import json
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

try:
    import litellm
    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False

from .scanner_config import get_config


class DocumentClassifier:
    """LLM-based document classifier."""
    
    # Prompt templates (can be overridden via .env)
    CLASSIFICATION_PROMPT = """Analyze this OCR text from a scanned document and classify it.

OCR Text:
{text}

Respond in JSON format:
{{
    "document_type": "invoice|receipt|letter|contract|form|id_document|other",
    "confidence": 0.0-1.0,
    "language": "pl|en|de|fr|other",
    "currency": "PLN|EUR|USD|GBP|null",
    "has_amount": true|false,
    "total_amount": number or null,
    "has_date": true|false,
    "date": "YYYY-MM-DD" or null,
    "has_nip": true|false,
    "nip": "string" or null,
    "vendor_name": "string" or null,
    "summary": "brief 1-line summary",
    "is_valid_document": true|false,
    "validation_issues": ["list of issues if any"]
}}

Be precise and only extract data that is clearly visible in the text."""

    RECEIPT_VALIDATION_PROMPT = """Analyze this OCR text to determine if it's a valid receipt/paragon.

OCR Text:
{text}

A valid receipt typically has:
- Store/vendor name
- Date of purchase
- List of items with prices
- Total amount
- Payment method or fiscal number

Respond in JSON:
{{
    "is_receipt": true|false,
    "confidence": 0.0-1.0,
    "vendor": "store name or null",
    "date": "YYYY-MM-DD or null",
    "total": number or null,
    "currency": "PLN|EUR|USD|null",
    "items_count": number,
    "has_fiscal_number": true|false,
    "issues": ["list of validation issues"]
}}"""

    INVOICE_VALIDATION_PROMPT = """Analyze this OCR text to determine if it's a valid invoice/faktura.

OCR Text:
{text}

A valid invoice typically has:
- Invoice number (numer faktury)
- Seller NIP and buyer NIP
- Issue date and payment due date
- Line items with quantities and prices
- Net amount, VAT, gross amount

Respond in JSON:
{{
    "is_invoice": true|false,
    "confidence": 0.0-1.0,
    "invoice_number": "string or null",
    "seller_nip": "string or null",
    "buyer_nip": "string or null",
    "issue_date": "YYYY-MM-DD or null",
    "due_date": "YYYY-MM-DD or null",
    "net_amount": number or null,
    "vat_amount": number or null,
    "gross_amount": number or null,
    "currency": "PLN|EUR|USD|null",
    "seller_name": "string or null",
    "buyer_name": "string or null",
    "issues": ["list of validation issues"]
}}"""

    def __init__(self, model: str = None, temperature: float = 0.1):
        config = get_config()
        self.model = model or config.llm_model
        self.temperature = temperature
        self.enabled = HAS_LITELLM and config.use_llm
        
        # Load custom prompts from env if available
        self.classification_prompt = os.getenv(
            "SQ_CLASSIFY_PROMPT", 
            self.CLASSIFICATION_PROMPT
        )
    
    def _call_llm(self, prompt: str) -> Optional[Dict]:
        """Call LLM and parse JSON response."""
        if not self.enabled:
            return None
        
        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"   ⚠️ LLM error: {e}")
            return None
    
    def classify_document(self, text: str) -> Dict[str, Any]:
        """Classify document using LLM."""
        if not text or len(text) < 20:
            return {
                "document_type": "unknown",
                "confidence": 0.0,
                "language": None,
            }
        
        # Truncate very long text
        text = text[:3000] if len(text) > 3000 else text
        
        prompt = self.classification_prompt.format(text=text)
        result = self._call_llm(prompt)
        
        if result:
            return result
        
        # Fallback to simple keyword detection
        return self._fallback_classify(text)
    
    def validate_receipt(self, text: str) -> Dict[str, Any]:
        """Validate if document is a valid receipt."""
        if not text:
            return {"is_receipt": False, "confidence": 0.0}
        
        text = text[:2000] if len(text) > 2000 else text
        prompt = self.RECEIPT_VALIDATION_PROMPT.format(text=text)
        result = self._call_llm(prompt)
        
        if result:
            return result
        
        return self._fallback_receipt_check(text)
    
    def validate_invoice(self, text: str) -> Dict[str, Any]:
        """Validate if document is a valid invoice."""
        if not text:
            return {"is_invoice": False, "confidence": 0.0}
        
        text = text[:2000] if len(text) > 2000 else text
        prompt = self.INVOICE_VALIDATION_PROMPT.format(text=text)
        result = self._call_llm(prompt)
        
        if result:
            return result
        
        return self._fallback_invoice_check(text)
    
    def extract_data(self, text: str, doc_type: str) -> Dict[str, Any]:
        """Extract structured data from document."""
        if doc_type == "receipt":
            return self.validate_receipt(text)
        elif doc_type == "invoice":
            return self.validate_invoice(text)
        else:
            return self.classify_document(text)
    
    def _fallback_classify(self, text: str) -> Dict[str, Any]:
        """Simple keyword-based classification as fallback."""
        text_lower = text.lower()
        
        # Detect language
        lang = "pl" if any(w in text_lower for w in ["zł", "faktura", "paragon", "nip"]) else \
               "en" if any(w in text_lower for w in ["invoice", "receipt", "total"]) else \
               "de" if any(w in text_lower for w in ["rechnung", "quittung", "€"]) else None
        
        # Detect type
        receipt_score = sum(1 for w in ["paragon", "fiskalny", "suma", "razem", "gotówka", "karta"] if w in text_lower)
        invoice_score = sum(1 for w in ["faktura", "nip", "vat", "netto", "brutto", "termin płatności"] if w in text_lower)
        
        if invoice_score > receipt_score and invoice_score >= 2:
            doc_type = "invoice"
            confidence = min(1.0, invoice_score * 0.2)
        elif receipt_score >= 2:
            doc_type = "receipt"
            confidence = min(1.0, receipt_score * 0.2)
        else:
            doc_type = "other"
            confidence = 0.3
        
        return {
            "document_type": doc_type,
            "confidence": confidence,
            "language": lang,
            "method": "fallback_keywords"
        }
    
    def _fallback_receipt_check(self, text: str) -> Dict[str, Any]:
        """Simple receipt check as fallback."""
        text_lower = text.lower()
        
        keywords = ["paragon", "fiskalny", "suma", "razem", "pln", "zł", "gotówka", "karta", "receipt", "total"]
        score = sum(1 for w in keywords if w in text_lower)
        
        return {
            "is_receipt": score >= 2,
            "confidence": min(1.0, score * 0.15),
            "method": "fallback"
        }
    
    def _fallback_invoice_check(self, text: str) -> Dict[str, Any]:
        """Simple invoice check as fallback."""
        text_lower = text.lower()
        
        keywords = ["faktura", "invoice", "nip", "vat", "netto", "brutto", "termin", "płatności"]
        score = sum(1 for w in keywords if w in text_lower)
        
        return {
            "is_invoice": score >= 2,
            "confidence": min(1.0, score * 0.15),
            "method": "fallback"
        }


# Global classifier instance
_classifier: Optional[DocumentClassifier] = None

def get_classifier() -> DocumentClassifier:
    """Get global classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = DocumentClassifier()
    return _classifier
