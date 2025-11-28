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
]
