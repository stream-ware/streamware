"""
LLM Component for Streamware

AI-powered text processing with Natural Language to DSL conversion.
Supports: SQL, Streamware Quick commands, Flow DSL, and custom conversions.
"""

from __future__ import annotations
import os
import json
import re
from typing import Any, Optional, Dict, List
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)

# Check for optional dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Ollama uses requests (usually available)
import requests
OLLAMA_AVAILABLE = True


@register("llm")
class LLMComponent(Component):
    """
    LLM operations component with DSL conversion
    
    Operations:
    - generate: Generate text from prompt
    - convert: Convert natural language to DSL
    - sql: Convert to SQL query
    - streamware: Convert to Streamware commands
    - analyze: Analyze and extract information
    - summarize: Summarize text
    - translate: Translate between languages
    
    URI Examples:
        llm://generate?prompt=Write a poem about coding
        llm://convert?to=sql&prompt=Get all users older than 30
        llm://sql?prompt=Find active orders from last week
        llm://streamware?prompt=Upload file to SSH server
        llm://analyze?prompt=Extract key points from this text
    
    Providers:
        - openai (default, requires OPENAI_API_KEY)
        - anthropic (requires ANTHROPIC_API_KEY)
        - ollama (local, free)
    """
    
    input_mime = "text/plain"
    output_mime = "text/plain"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "generate"
        
        # Provider configuration
        self.provider = uri.get_param("provider", os.environ.get("LLM_PROVIDER", "openai"))
        self.model = uri.get_param("model", self._get_default_model())
        
        # API keys
        self.openai_key = uri.get_param("openai_key", os.environ.get("OPENAI_API_KEY"))
        self.anthropic_key = uri.get_param("anthropic_key", os.environ.get("ANTHROPIC_API_KEY"))
        self.ollama_url = uri.get_param("ollama_url", os.environ.get("OLLAMA_URL", "http://localhost:11434"))
        
        # Parameters
        self.prompt = uri.get_param("prompt")
        self.system = uri.get_param("system")
        self.temperature = float(uri.get_param("temperature", 0.7))
        self.max_tokens = int(uri.get_param("max_tokens", 2000))
        
        # DSL conversion target
        self.to_dsl = uri.get_param("to", "sql")
        
        # Validate provider
        if self.provider == "openai" and not OPENAI_AVAILABLE and not self.openai_key:
            logger.warning("OpenAI not available, falling back to Ollama")
            self.provider = "ollama"
        elif self.provider == "anthropic" and not ANTHROPIC_AVAILABLE and not self.anthropic_key:
            logger.warning("Anthropic not available, falling back to Ollama")
            self.provider = "ollama"
    
    def _get_default_model(self) -> str:
        """Get default model for provider"""
        models = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-sonnet-20241022",
            "ollama": "llama3.2:latest"
        }
        return models.get(self.provider, "gpt-4o-mini")
    
    def process(self, data: Any) -> Any:
        """Process LLM operation"""
        logger.info(f"LLM operation: {self.operation} with {self.provider}")
        
        operations = {
            "generate": self._generate,
            "convert": self._convert_to_dsl,
            "sql": self._convert_to_sql,
            "streamware": self._convert_to_streamware,
            "analyze": self._analyze,
            "summarize": self._summarize,
            "translate": self._translate,
            "chat": self._chat,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown LLM operation: {self.operation}")
        
        return operation_func(data)
    
    def _generate(self, data: Any) -> str:
        """Generate text from prompt"""
        prompt = self.prompt or str(data)
        
        if not prompt:
            raise ComponentError("No prompt provided")
        
        return self._call_llm(prompt)
    
    def _convert_to_dsl(self, data: Any) -> str:
        """Convert natural language to DSL"""
        input_text = self.prompt or str(data)
        target_dsl = self.to_dsl
        
        system_prompts = {
            "sql": """You are an expert SQL query generator. Convert natural language requests to SQL queries.
Output ONLY the SQL query, no explanations or markdown.
Use standard SQL syntax compatible with PostgreSQL.""",
            
            "streamware": """You are an expert in Streamware CLI commands. Convert natural language requests to Streamware 'sq' commands.
Output ONLY the command, no explanations or markdown.
Use the 'sq' quick command format.

Examples:
- "upload file to ssh server" -> sq ssh prod.com --upload file.txt --remote /data/
- "get users from api" -> sq get api.com/users --json
- "save to database" -> sq postgres "INSERT INTO table VALUES (...)" """,
            
            "bash": """You are an expert bash script writer. Convert natural language to bash commands.
Output ONLY the command or script, no explanations.""",
            
            "python": """You are an expert Python programmer. Convert natural language to Python code.
Output ONLY the Python code, no explanations or markdown.""",
        }
        
        system = system_prompts.get(target_dsl, f"Convert to {target_dsl} format.")
        
        prompt = f"{system}\n\nInput: {input_text}\n\nOutput:"
        
        result = self._call_llm(prompt, system=system)
        
        # Clean up result (remove markdown, etc.)
        result = self._clean_dsl_output(result, target_dsl)
        
        return result
    
    def _convert_to_sql(self, data: Any) -> str:
        """Convert natural language to SQL"""
        self.to_dsl = "sql"
        return self._convert_to_dsl(data)
    
    def _convert_to_streamware(self, data: Any) -> str:
        """Convert natural language to Streamware commands"""
        self.to_dsl = "streamware"
        return self._convert_to_dsl(data)
    
    def _analyze(self, data: Any) -> Dict:
        """Analyze text and extract information"""
        text = self.prompt or str(data)
        
        system = """You are a text analysis expert. Analyze the given text and return JSON with:
- summary: Brief summary
- key_points: List of key points
- sentiment: positive/negative/neutral
- entities: Important entities mentioned
- topics: Main topics

Return ONLY valid JSON."""
        
        prompt = f"Analyze this text:\n\n{text}"
        
        result = self._call_llm(prompt, system=system)
        
        # Try to parse as JSON
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw_analysis": result}
    
    def _summarize(self, data: Any) -> str:
        """Summarize text"""
        text = self.prompt or str(data)
        
        system = "You are a summarization expert. Provide concise, accurate summaries."
        prompt = f"Summarize this text in 2-3 sentences:\n\n{text}"
        
        return self._call_llm(prompt, system=system)
    
    def _translate(self, data: Any) -> str:
        """Translate text"""
        text = self.prompt or str(data)
        target_lang = self.to_dsl or "English"
        
        system = f"You are a professional translator. Translate to {target_lang}."
        prompt = f"Translate this text to {target_lang}:\n\n{text}"
        
        return self._call_llm(prompt, system=system)
    
    def _chat(self, data: Any) -> str:
        """Chat completion"""
        message = self.prompt or str(data)
        return self._call_llm(message)
    
    def _call_llm(self, prompt: str, system: str = None) -> str:
        """Call LLM provider"""
        if self.provider == "openai":
            return self._call_openai(prompt, system)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt, system)
        elif self.provider == "ollama":
            return self._call_ollama(prompt, system)
        else:
            raise ComponentError(f"Unknown LLM provider: {self.provider}")
    
    def _call_openai(self, prompt: str, system: str = None) -> str:
        """Call OpenAI API"""
        if not OPENAI_AVAILABLE:
            raise ComponentError("openai package not installed")
        
        if not self.openai_key:
            raise ComponentError("OPENAI_API_KEY not set")
        
        client = openai.OpenAI(api_key=self.openai_key)
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        return response.choices[0].message.content
    
    def _call_anthropic(self, prompt: str, system: str = None) -> str:
        """Call Anthropic API"""
        if not ANTHROPIC_AVAILABLE:
            raise ComponentError("anthropic package not installed")
        
        if not self.anthropic_key:
            raise ComponentError("ANTHROPIC_API_KEY not set")
        
        client = anthropic.Anthropic(api_key=self.anthropic_key)
        
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system:
            kwargs["system"] = system
        
        response = client.messages.create(**kwargs)
        
        return response.content[0].text
    
    def _call_ollama(self, prompt: str, system: str = None) -> str:
        """Call Ollama API"""
        url = f"{self.ollama_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except requests.exceptions.RequestException as e:
            raise ComponentError(f"Ollama API error: {e}")
    
    def _clean_dsl_output(self, text: str, dsl_type: str) -> str:
        """Clean DSL output (remove markdown, etc.)"""
        # Remove markdown code blocks
        text = re.sub(r'```[\w]*\n', '', text)
        text = re.sub(r'```\n?', '', text)
        
        # Remove common prefixes
        text = re.sub(r'^(SQL:|Query:|Command:)\s*', '', text, flags=re.IGNORECASE)
        
        # Clean whitespace
        text = text.strip()
        
        return text


# Quick helper functions
def llm_generate(prompt: str, provider: str = "openai", model: str = None) -> str:
    """Quick LLM text generation"""
    from ..core import flow
    
    uri = f"llm://generate?prompt={prompt}&provider={provider}"
    if model:
        uri += f"&model={model}"
    
    return flow(uri).run()


def llm_to_sql(natural_language: str, provider: str = "openai") -> str:
    """Quick natural language to SQL conversion"""
    from ..core import flow
    
    uri = f"llm://sql?prompt={natural_language}&provider={provider}"
    return flow(uri).run()


def llm_to_streamware(natural_language: str, provider: str = "openai") -> str:
    """Quick natural language to Streamware commands"""
    from ..core import flow
    
    uri = f"llm://streamware?prompt={natural_language}&provider={provider}"
    return flow(uri).run()


def llm_analyze(text: str, provider: str = "openai") -> Dict:
    """Quick text analysis"""
    from ..core import flow
    
    uri = f"llm://analyze?prompt={text}&provider={provider}"
    return flow(uri).run()
