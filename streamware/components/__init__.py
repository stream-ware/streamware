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

from .vscode_bot import (
    VSCodeBotComponent,
    click_accept,
    click_reject,
    continue_bot,
)

from .voice_mouse import (
    VoiceMouseComponent,
    voice_click,
    listen_and_click,
)

from .voice_keyboard import (
    VoiceKeyboardComponent,
    voice_type,
    voice_press,
    dictate,
)

from .stream import (
    StreamComponent,
    analyze_stream,
    analyze_screen,
    analyze_youtube,
    watch_screen,
)

from .network_scan import (
    NetworkScanComponent,
    scan_network,
    find_devices,
    find_cameras,
    find_raspberry_pi,
    find_printers,
)

from .tracking import (
    TrackingComponent,
    detect_objects as tracking_detect,
    track_person,
    count_people,
    monitor_zone,
    detect_vehicles,
)

from .motion_diff import (
    MotionDiffComponent,
    detect_motion,
    analyze_motion,
    get_motion_regions,
)

from .smart_monitor import (
    SmartMonitorComponent,
    smart_monitor,
    quick_watch,
    monitor_zones,
)

from .live_narrator import (
    LiveNarratorComponent,
    live_narrator,
    watch_for,
    describe_now,
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
    
    # VSCode Bot
    "VSCodeBotComponent",
    "click_accept",
    "click_reject",
    "continue_bot",
    
    # Voice Mouse
    "VoiceMouseComponent",
    "voice_click",
    "listen_and_click",
    
    # Voice Keyboard
    "VoiceKeyboardComponent",
    "voice_type",
    "voice_press",
    "dictate",
    
    # Stream (real-time)
    "StreamComponent",
    "analyze_stream",
    "analyze_screen",
    "analyze_youtube",
    "watch_screen",
    
    # Network scan
    "NetworkScanComponent",
    "scan_network",
    "find_devices",
    "find_cameras",
    "find_raspberry_pi",
    "find_printers",
    
    # Tracking
    "TrackingComponent",
    "tracking_detect",
    "track_person",
    "count_people",
    "monitor_zone",
    "detect_vehicles",
    
    # Motion (smart region-based)
    "MotionDiffComponent",
    "detect_motion",
    "analyze_motion",
    "get_motion_regions",
    
    # Smart Monitor (buffered, adaptive)
    "SmartMonitorComponent",
    "smart_monitor",
    "quick_watch",
    "monitor_zones",
    
    # Live Narrator (TTS, triggers)
    "LiveNarratorComponent",
    "live_narrator",
    "watch_for",
    "describe_now",
]
