"""
LLM Component for Streamware

AI-powered text processing with Natural Language to DSL conversion.
Supports: SQL, Streamware Quick commands, Flow DSL, and custom conversions.

Provider format (LiteLLM compatible):
    provider="openai/gpt-4o"
    provider="ollama/qwen2.5:14b"
    provider="anthropic/claude-3-5-sonnet-20240620"
    provider="gemini/gemini-2.0-flash"
    provider="groq/llama3-70b-8192"
    provider="deepseek/deepseek-chat"
"""

from __future__ import annotations
import os
import json
import re
import subprocess
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

# Try LiteLLM for unified provider access
try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# Ollama uses requests (usually available)
import requests
OLLAMA_AVAILABLE = True

# Provider -> API key environment variable mapping
PROVIDER_API_KEYS = {
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "mistral": ["MISTRAL_API_KEY"],
    "cohere": ["COHERE_API_KEY"],
    "together": ["TOGETHER_API_KEY", "TOGETHERAI_API_KEY"],
    "fireworks": ["FIREWORKS_API_KEY"],
    "anyscale": ["ANYSCALE_API_KEY"],
    "perplexity": ["PERPLEXITY_API_KEY"],
    "ollama": [],  # No key needed
}

# Default models per provider
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
    "ollama": "llama3.2:latest",
    "gemini": "gemini-2.0-flash",
    "groq": "llama3-70b-8192",
    "deepseek": "deepseek-chat",
    "mistral": "mistral-large-latest",
}


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
        llm://generate?prompt=Write a poem&provider=openai/gpt-4o
        llm://generate?prompt=Hello&provider=ollama/qwen2.5:14b
        llm://sql?prompt=Get all users&provider=gemini/gemini-2.0-flash
        llm://analyze?prompt=Extract points&provider=groq/llama3-70b-8192
    
    Provider format (LiteLLM compatible):
        openai/gpt-4o, openai/gpt-4o-mini, openai/o1-mini
        anthropic/claude-3-5-sonnet-20240620, anthropic/claude-3-haiku-20240307
        ollama/llama3.2, ollama/qwen2.5:14b, ollama/llava
        gemini/gemini-2.0-flash, gemini/gemini-1.5-pro
        groq/llama3-70b-8192, groq/llama3-8b-8192
        deepseek/deepseek-chat
        
    API keys are auto-detected from environment:
        OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, etc.
    """
    
    input_mime = "text/plain"
    output_mime = "text/plain"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "generate"
        
        # Parse provider in LiteLLM format: "provider/model" or just "provider"
        from ..config import config
        default_provider = config.get("SQ_LLM_PROVIDER", "openai")
        default_model = config.get("SQ_MODEL", "gpt-4o-mini")
        
        provider_param = uri.get_param("provider")
        if not provider_param:
            # Construct from config if not in URI
            if default_provider == "openai" and default_model:
                provider_param = f"openai/{default_model}"
            elif default_provider == "ollama" and default_model:
                provider_param = f"ollama/{default_model}"
            else:
                provider_param = f"{default_provider}/{default_model}"
                
        self.provider, self.model = self._parse_provider(provider_param)
        
        # Override model if explicitly specified
        explicit_model = uri.get_param("model")
        if explicit_model:
            self.model = explicit_model
        
        # Auto-detect API key from environment
        self.api_key = uri.get_param("api_key") or uri.get_param("api_token") or self._get_api_key()
        
        # Custom base URL (for proxies, local deployments)
        self.base_url = uri.get_param("base_url", os.environ.get(f"{self.provider.upper()}_BASE_URL"))
        self.ollama_url = uri.get_param("ollama_url", config.get("SQ_OLLAMA_URL", "http://localhost:11434"))
        
        # Parameters
        self.prompt = uri.get_param("prompt")
        self.system = uri.get_param("system")
        self.temperature = float(uri.get_param("temperature", 0.7))
        self.max_tokens = int(uri.get_param("max_tokens", 2000))
        
        # DSL conversion target
        self.to_dsl = uri.get_param("to", "sql")
        
        # Auto-install litellm if using non-standard provider
        if self.provider not in ["openai", "anthropic", "ollama"] and not LITELLM_AVAILABLE:
            self._ensure_litellm()
        
        # Validate provider availability
        self._validate_provider()
        
        logger.info(f"LLM initialized: {self.provider}/{self.model}")
    
    def _parse_provider(self, provider_str: str) -> tuple:
        """Parse provider string in format 'provider/model' or 'provider'"""
        if "/" in provider_str:
            parts = provider_str.split("/", 1)
            provider = parts[0].lower()
            model = parts[1]
            return provider, model
        else:
            provider = provider_str.lower()
            model = DEFAULT_MODELS.get(provider, "gpt-4o-mini")
            return provider, model
    
    def _get_api_key(self) -> Optional[str]:
        """Auto-detect API key from environment variables"""
        env_vars = PROVIDER_API_KEYS.get(self.provider, [])
        for var in env_vars:
            key = os.environ.get(var)
            if key:
                return key
        return None
    
    def _ensure_litellm(self):
        """Install litellm if needed for non-standard providers"""
        global LITELLM_AVAILABLE, litellm
        try:
            import litellm
            LITELLM_AVAILABLE = True
        except ImportError:
            logger.info("Installing litellm for extended provider support...")
            try:
                subprocess.run(["pip", "install", "litellm"], check=True, capture_output=True)
                import litellm
                LITELLM_AVAILABLE = True
            except Exception as e:
                logger.warning(f"Could not install litellm: {e}")
    
    def _validate_provider(self):
        """Validate provider is available"""
        if self.provider == "ollama":
            return  # Ollama doesn't need API key
        
        if self.provider in ["openai", "anthropic", "gemini", "groq", "deepseek", "mistral"]:
            if not self.api_key and self.provider != "ollama":
                env_vars = PROVIDER_API_KEYS.get(self.provider, [])
                logger.warning(
                    f"No API key found for {self.provider}. "
                    f"Set one of: {', '.join(env_vars)}"
                )
                # Try falling back to Ollama
                if OLLAMA_AVAILABLE:
                    logger.info("Falling back to Ollama")
                    self.provider = "ollama"
                    self.model = DEFAULT_MODELS["ollama"]
    
    def process(self, data: Any) -> Any:
        """Process LLM operation"""
        # Normalize legacy / alias operation names
        op = self.operation
        if op == "to_sql":
            op = "sql"
        
        logger.info(f"LLM operation: {op} with {self.provider}")
        
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
        
        operation_func = operations.get(op)
        if not operation_func:
            raise ComponentError(f"Unknown LLM operation: {self.operation}")
        
        return operation_func(data)
    
    def _generate(self, data: Any) -> str:
        """Generate text from prompt"""
        prompt = self.prompt if self.prompt else (str(data) if data else None)
        
        if not prompt or not prompt.strip():
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
        # Use LiteLLM for unified access if available and not using native providers
        if LITELLM_AVAILABLE and self.provider not in ["ollama"]:
            return self._call_litellm(prompt, system)
        
        # Native provider implementations
        if self.provider == "openai":
            return self._call_openai(prompt, system)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt, system)
        elif self.provider == "ollama":
            return self._call_ollama(prompt, system)
        elif self.provider in ["gemini", "groq", "deepseek", "mistral", "cohere", "together"]:
            # Try LiteLLM, or fall back to direct API
            if LITELLM_AVAILABLE:
                return self._call_litellm(prompt, system)
            else:
                return self._call_generic_openai_compatible(prompt, system)
        else:
            raise ComponentError(f"Unknown LLM provider: {self.provider}")
    
    def _call_litellm(self, prompt: str, system: str = None) -> str:
        """Call LLM via LiteLLM (unified interface for all providers)"""
        try:
            import litellm
            
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            # Format model name for LiteLLM
            model_name = f"{self.provider}/{self.model}"
            
            response = litellm.completion(
                model=model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=self.api_key,
                base_url=self.base_url,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise ComponentError(f"LiteLLM error ({self.provider}): {e}")
    
    def _call_generic_openai_compatible(self, prompt: str, system: str = None) -> str:
        """Call OpenAI-compatible API (Groq, Together, etc.)"""
        # Many providers use OpenAI-compatible APIs
        base_urls = {
            "groq": "https://api.groq.com/openai/v1",
            "together": "https://api.together.xyz/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "mistral": "https://api.mistral.ai/v1",
            "fireworks": "https://api.fireworks.ai/inference/v1",
            "anyscale": "https://api.endpoints.anyscale.com/v1",
            "perplexity": "https://api.perplexity.ai",
        }
        
        base_url = self.base_url or base_urls.get(self.provider)
        if not base_url:
            raise ComponentError(f"No base URL for provider: {self.provider}")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            raise ComponentError(f"{self.provider} API error: {e}")
    
    def _call_openai(self, prompt: str, system: str = None) -> str:
        """Call OpenAI API"""
        if not OPENAI_AVAILABLE:
            raise ComponentError("openai package not installed")
        
        if not self.api_key:
            raise ComponentError("OPENAI_API_KEY not set")
        
        client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        
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
        
        if not self.api_key:
            raise ComponentError("ANTHROPIC_API_KEY not set")
        
        client = anthropic.Anthropic(api_key=self.api_key)
        
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


# Alias for compatibility
generate_text = llm_generate


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
