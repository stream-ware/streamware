przeniesð dokumentacje do folderu docs/*
poukładaj w folderach i zrob foldery docs/v1  i docs/v2 aby rozdzielić stare wersje, ktore nie są aktualne na ten aktualny stan projektu pi przenieść do v1

Sparwdz czy dokumentacja v2 jest zgodna z aktuazlnym stanem i posegreguj pliki z ./*.md (poza readme, changelog i todo) do odpowiednich podfolderow w docs/*

Dodatkowo zaktualizuj examples, aby uzywały krótkiego zapisu streamware quick, aby pokazać możliwości, jeśli coś wyamga dodatkowego kodu python, to stwoórż nowy components/*

zadbaj o to by użycie streamware quick nie wymagało od operatora dodatkowych instalacji, aby to działo się podczas używania sq

wykrywaj providerów i zrób automatyczne podpinanie wedle


 wprowadź poprawki do przykładów i architektury, oraz przy obsłudze róznych providerów LLM
Here you can use any provider that Litellm library supports, for instance: ollama/qwen2
            # provider="ollama/qwen2", api_token="no-token", 
            llm_config = LLMConfig(provider="openai/gpt-4o", api_token=os.getenv('OPENAI_API_KEY')), 
            schema=OpenAIModelFee.schema(),
            extraction_type="schema",
            instruction="""From the crawled content, extract all mentioned model names along with their fees for input and output tokens. 
            Do not miss any models in the entire content. One extracted model JSON format should look like this: 
            {"model_name": "GPT-4", "input_fee": "US$10.00 / 1M tokens", "output_fee": "US$30.00 / 1M tokens"}."""
        ),            


LLMConfig is useful to pass LLM provider config to strategies and functions that rely on LLMs to do extraction, filtering, schema generation etc. Currently it can be used in the following -
LLMExtractionStrategy
LLMContentFilter
JsonCssExtractionStrategy.generate_schema
JsonXPathExtractionStrategy.generate_schema
3.1 Parameters
ParameterType / DefaultWhat It Does
provider
"ollama/llama3","groq/llama3-70b-8192","groq/llama3-8b-8192", "openai/gpt-4o-mini" ,"openai/gpt-4o","openai/o1-mini","openai/o1-preview","openai/o3-mini","openai/o3-mini-high","anthropic/claude-3-haiku-20240307","anthropic/claude-3-opus-20240229","anthropic/claude-3-sonnet-20240229","anthropic/claude-3-5-sonnet-20240620","gemini/gemini-pro","gemini/gemini-1.5-pro","gemini/gemini-2.0-flash","gemini/gemini-2.0-flash-exp","gemini/gemini-2.0-flash-lite-preview-02-05","deepseek/deepseek-chat"
(default: "openai/gpt-4o-mini")
Which LLM provider to use.
api_token
1.Optional. When not provided explicitly, api_token will be read from environment variables based on provider. For example: If a gemini model is passed as provider then,"GEMINI_API_KEY" will be read from environment variables
2. API token of LLM provider
eg: api_token = "gsk_1ClHGGJ7Lpn4WGybR7vNWGdyb3FY7zXEw3SCiy0BAVM9lL8CQv"
3. Environment variable - use with prefix "env:"
eg:api_token = "env: GROQ_API_KEY"
API token to use for the given provider
base_url
Optional. Custom API endpoint
If your provider has a custom endpoint
3.2 Example Usage
llm_config = LLMConfig(provider="openai/gpt-4o-mini", api_token=os.getenv("OPENAI_API_KEY"))
