"""Curated list of upstream LLM providers + their default endpoints + models.

The wizard uses this to populate the provider-picker dropdown. Each provider
maps to a FortiAIGate `aiProvider[].executor` value plus a default `endpoint`
URL. If the partner picks a non-default endpoint we auto-flip
`privateEndpointEnabled: true` (lab-verified gotcha — GLM hit this).

Source: api/reference/04-providers.md + the verified GLM/OpenAI/Anthropic
builds in the multi-tenant smoke test.
"""

PROVIDERS = {
    "anthropic": {
        "label": "Anthropic Claude",
        "executor": "anthropic",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "models": [
            "claude-sonnet-4-6",
            "claude-opus-4-7",
            "claude-haiku-4-5",
        ],
        "key_format": "sk-ant-...",
        "key_hint": "Get one at console.anthropic.com",
        "supports_private_endpoint": False,
        "notes": "Default upstream for Acme/Customer_1 demo. Verified working.",
    },
    "openai": {
        "label": "OpenAI",
        "executor": "openai",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "o1",
            "o1-mini",
        ],
        "key_format": "sk-proj-... or sk-...",
        "key_hint": "Get one at platform.openai.com/api-keys",
        "supports_private_endpoint": True,
        "notes": "Default upstream for Beta Health/Customer_2 demo. Verified working with strict-block policy.",
    },
    "azure-openai": {
        "label": "Azure OpenAI",
        "executor": "openai",
        "endpoint": "",
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-35-turbo",
        ],
        "key_format": "32-char Azure key",
        "key_hint": "Azure portal -> your OpenAI resource -> Keys and Endpoint",
        "supports_private_endpoint": True,
        "endpoint_hint": "https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2024-08-01-preview",
        "notes": "Uses OpenAI executor with privateEndpointEnabled=true. Endpoint must be the full deployment URL.",
    },
    "aws-bedrock": {
        "label": "AWS Bedrock",
        "executor": "aws-bedrock",
        "endpoint": "",
        "models": [
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "anthropic.claude-3-5-haiku-20241022-v1:0",
            "anthropic.claude-opus-4-20250514-v1:0",
            "meta.llama3-1-70b-instruct-v1:0",
        ],
        "key_format": "Access Key ID + Secret + Region",
        "key_hint": "IAM user with bedrock:InvokeModel permission",
        "supports_private_endpoint": False,
        "needs_aws_creds": True,
        "notes": "Requires accessKeyId, secretAccessKey, and regionName instead of a single API key.",
    },
    "google-vertex": {
        "label": "Google Vertex AI",
        "executor": "google",
        "endpoint": "",
        "models": [
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
        "key_format": "Service account JSON or OAuth token",
        "key_hint": "GCP console -> IAM -> Service Accounts",
        "supports_private_endpoint": True,
        "notes": "Vertex executor. Endpoint format includes project ID and region.",
    },
    "zhipu-glm": {
        "label": "Zhipu GLM (China sovereign)",
        "executor": "openai",
        "endpoint": "https://open.bigmodel.cn/api/paas/v4",
        "models": [
            "glm-4-plus",
            "glm-4.6",
            "glm-4.5",
            "glm-4.5-air",
            "glm-4.5-flash",
        ],
        "key_format": "uuid.token (e.g. cd5ea74769534f368c886c48eb84e9ad.TblmHAEm6xlANu4G)",
        "key_hint": "Get one at open.bigmodel.cn -> API Keys",
        "supports_private_endpoint": True,
        "force_private_endpoint": True,
        "notes": "Uses OpenAI-compatible API. Must set privateEndpointEnabled=true since endpoint is non-default. Verified for Customer_3 (Coastal-Pacific sovereign-AI demo).",
    },
    "custom": {
        "label": "Custom / Bring your own (OpenAI-compatible)",
        "executor": "openai",
        "endpoint": "",
        "models": [],
        "key_format": "Provider-specific",
        "key_hint": "Use this for vLLM, LM Studio, Ollama, DeepSeek, Mistral, or any OpenAI-compatible API.",
        "supports_private_endpoint": True,
        "force_private_endpoint": True,
        "notes": "OpenAI-compatible endpoints (e.g. http://internal-vllm:8000/v1) work via openai executor + privateEndpointEnabled=true.",
    },
}


def get_provider(provider_id: str) -> dict:
    if provider_id not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider_id}")
    return PROVIDERS[provider_id]


def needs_private_endpoint(provider_id: str, endpoint: str) -> bool:
    """Decide if privateEndpointEnabled must be true for this provider+endpoint.

    Logic (matches 05-onboard-tenant.sh):
      - provider has force_private_endpoint flag -> always true
      - provider has a default endpoint and user picked something else -> true
      - otherwise -> false
    """
    p = PROVIDERS.get(provider_id, {})
    if p.get("force_private_endpoint"):
        return True
    default_ep = p.get("endpoint", "")
    if default_ep and endpoint and endpoint.rstrip("/") != default_ep.rstrip("/"):
        return True
    return False
