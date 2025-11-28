"""
Streamware Components Package
"""

from .curllm import (
    CurLLMComponent,
    CurLLMStreamComponent,
    WebComponent,
    browse,
    extract_data,
    fill_form,
    execute_bql,
)

from .file import (
    FileReadComponent,
    FileWriteComponent,
    FileWatchComponent,
)

from .transform import (
    TransformComponent,
    JSONPathComponent,
    TemplateComponent,
    CSVComponent,
)

from .kafka import (
    KafkaProduceComponent,
    KafkaConsumeComponent,
)

from .rabbitmq import (
    RabbitMQPublishComponent,
    RabbitMQConsumeComponent,
)

from .postgres import (
    PostgresQueryComponent,
    PostgresInsertComponent,
    PostgresStreamComponent,
)

from .http import (
    HTTPComponent,
)

# Communication components
from .email import (
    EmailComponent,
    EmailWatchComponent,
    EmailFilterComponent,
)

from .telegram import (
    TelegramComponent,
    TelegramBotComponent,
    TelegramCommandComponent,
)

from .whatsapp import (
    WhatsAppComponent,
    WhatsAppWebhookComponent,
)

from .discord import (
    DiscordComponent,
    DiscordBotComponent,
    DiscordSlashComponent,
)

from .slack import (
    SlackComponent,
    SlackEventsComponent,
    SlackSlashComponent,
)

from .sms import (
    SMSComponent,
    SMSWebhookComponent,
)

from .ssh import (
    SSHComponent,
    ssh_upload,
    ssh_download,
    ssh_exec,
    ssh_deploy,
)

from .llm import (
    LLMComponent,
    llm_generate,
    llm_to_sql,
    llm_to_streamware,
    llm_analyze,
)

from .video import (
    VideoComponent,
    video_from_rtsp,
    detect_objects,
    generate_caption,
)

from .text2streamware import (
    Text2StreamwareComponent,
    text_to_sq,
    explain_command,
    optimize_command,
)

from .deploy import (
    DeployComponent,
    deploy_k8s,
    deploy_compose,
    scale_k8s,
)

from .setup import (
    SetupComponent,
    auto_install,
    check_deps,
)

from .template import (
    TemplateComponent,
    generate_project,
)

from .registry import (
    RegistryComponent,
    lookup_component,
    list_models,
)

from .webapp import (
    WebAppComponent,
    create_webapp,
)

from .desktop import (
    DesktopAppComponent,
    create_desktop_app,
)

from .media import (
    MediaComponent,
    describe_video,
    transcribe,
    speak,
)

from .service import (
    ServiceComponent,
    start_service,
    stop_service,
    service_status,
)

from .voice import (
    VoiceComponent,
    listen,
    speak,
    voice_command,
)

from .automation import (
    AutomationComponent,
    click,
    type_text,
    automate,
)

__all__ = [
    # CurLLM
    "CurLLMComponent",
    "CurLLMStreamComponent",
    "WebComponent",
    "browse",
    "extract_data",
    "fill_form",
    "execute_bql",
    
    # File
    "FileReadComponent",
    "FileWriteComponent",
    "FileWatchComponent",
    
    # Transform
    "TransformComponent",
    "JSONPathComponent",
    "TemplateComponent",
    "CSVComponent",
    
    # Kafka
    "KafkaProduceComponent",
    "KafkaConsumeComponent",
    
    # RabbitMQ
    "RabbitMQPublishComponent",
    "RabbitMQConsumeComponent",
    
    # PostgreSQL
    "PostgresQueryComponent",
    "PostgresInsertComponent",
    "PostgresStreamComponent",
    
    # HTTP
    "HTTPComponent",
    
    # Email
    "EmailComponent",
    "EmailWatchComponent",
    "EmailFilterComponent",
    
    # Telegram
    "TelegramComponent",
    "TelegramBotComponent",
    "TelegramCommandComponent",
    
    # WhatsApp
    "WhatsAppComponent",
    "WhatsAppWebhookComponent",
    
    # Discord
    "DiscordComponent",
    "DiscordBotComponent",
    "DiscordSlashComponent",
    
    # Slack
    "SlackComponent",
    "SlackEventsComponent",
    "SlackSlashComponent",
    
    # SMS
    "SMSComponent",
    "SMSWebhookComponent",
    
    # SSH
    "SSHComponent",
    "ssh_upload",
    "ssh_download",
    "ssh_exec",
    "ssh_deploy",
    
    # LLM
    "LLMComponent",
    "llm_generate",
    "llm_to_sql",
    "llm_to_streamware",
    "llm_analyze",
    
    # Video
    "VideoComponent",
    "video_from_rtsp",
    "detect_objects",
    "generate_caption",
    
    # Text2Streamware
    "Text2StreamwareComponent",
    "text_to_sq",
    "explain_command",
    "optimize_command",
    
    # Deploy
    "DeployComponent",
    "deploy_k8s",
    "deploy_compose",
    "scale_k8s",
    
    # Setup
    "SetupComponent",
    "auto_install",
    "check_deps",
    
    # Template
    "TemplateComponent",
    "generate_project",
    
    # Registry
    "RegistryComponent",
    "lookup_component",
    "list_models",
    
    # WebApp
    "WebAppComponent",
    "create_webapp",
    
    # Desktop
    "DesktopAppComponent",
    "create_desktop_app",
    
    # Media
    "MediaComponent",
    "describe_video",
    "transcribe",
    "speak",
    
    # Service
    "ServiceComponent",
    "start_service",
    "stop_service",
    "service_status",
    
    # Voice
    "VoiceComponent",
    "listen",
    "speak",
    "voice_command",
    
    # Automation
    "AutomationComponent",
    "click",
    "type_text",
    "automate",
]
