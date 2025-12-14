"""
CLI Handlers - Miscellaneous Commands

Handlers for: visualize, mqtt, shell, functions, voice_shell, accounting
"""

import sys
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse


def handle_visualize(args) -> int:
    """Handle real-time visualization command."""
    from .realtime_visualizer import start_visualizer
    
    width = args.width
    height = args.height
    fps = args.fps
    video_mode = getattr(args, 'video_mode', 'ws')
    transport = getattr(args, 'transport', 'tcp')
    backend = getattr(args, 'backend', 'opencv')
    
    if getattr(args, 'fast', False):
        width = min(width, 320)
        height = min(height, 240)
        fps = min(15, max(fps, 10))
        print("⚡ Fast mode enabled")
    
    if getattr(args, 'turbo', False):
        backend = 'pyav'
        transport = 'udp'
        video_mode = 'meta'
        width = min(width, 320)
        height = min(height, 240)
        fps = max(fps, 10)
        print("🚀 TURBO mode: PyAV + UDP + metadata-only")
    
    print(f"\n🎯 Starting Real-time Motion Visualizer")
    print(f"   URL: {args.url}")
    print(f"   Port: {args.port}")
    print(f"   FPS: {fps}")
    print(f"   Size: {width}x{height}")
    print(f"   Mode: {video_mode.upper()}")
    print(f"   Backend: {backend.upper()}")
    print(f"   Transport: {transport.upper()}")
    print(f"\n   Open http://localhost:{args.port} in browser\n")
    
    try:
        start_visualizer(
            rtsp_url=args.url,
            port=args.port,
            fps=fps,
            width=width,
            height=height,
            use_simple=getattr(args, 'simple', False),
            video_mode=video_mode,
            transport=transport,
            backend=backend,
        )
    except KeyboardInterrupt:
        print("\n🛑 Visualizer stopped")
    
    return 0


def handle_mqtt(args) -> int:
    """Handle MQTT DSL publisher command."""
    from .realtime_visualizer import start_mqtt_publisher
    
    print(f"\n📡 Starting MQTT DSL Publisher")
    print(f"   RTSP: {args.url}")
    print(f"   Broker: {args.broker}:{args.mqtt_port}")
    print(f"   Topic: {args.topic}/*")
    print(f"   FPS: {args.fps}")
    print(f"   Motion threshold: {args.threshold}%")
    print()
    
    try:
        start_mqtt_publisher(
            rtsp_url=args.url,
            mqtt_broker=args.broker,
            mqtt_port=args.mqtt_port,
            mqtt_username=args.username,
            mqtt_password=args.password,
            topic_prefix=args.topic,
            fps=args.fps,
            width=args.width,
            height=args.height,
            motion_threshold=args.threshold,
        )
    except KeyboardInterrupt:
        print("\n🛑 MQTT Publisher stopped")
    
    return 0


def handle_shell(args) -> int:
    """Handle interactive LLM shell command."""
    from .llm_shell import LLMShell
    
    shell = LLMShell(
        model=args.model,
        provider=args.provider,
        auto_execute=args.auto,
        verbose=args.verbose,
    )
    
    shell.run()
    return 0


def handle_voice_shell(args) -> int:
    """Handle voice shell server command."""
    try:
        from .voice_shell_server import VoiceShellServer
        import asyncio
        
        verbose = getattr(args, 'verbose', False)
        lang = getattr(args, 'lang', 'en')
        
        server = VoiceShellServer(
            host=args.host,
            port=args.port,
            model=args.model,
            verbose=verbose,
            default_language=lang,
        )
        
        asyncio.run(server.run())
        return 0
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Install with: pip install websockets")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def handle_functions(args) -> int:
    """Handle functions listing command."""
    from .function_registry import registry, get_llm_context
    
    if args.json:
        print(registry.to_json())
        return 0
    
    if args.llm:
        print(get_llm_context())
        return 0
    
    print("=" * 60)
    print("Available Functions for LLM")
    print("=" * 60)
    print()
    
    for cat in registry.categories():
        if args.category and cat != args.category:
            continue
        
        print(f"📂 {cat.upper()}")
        print("-" * 40)
        
        for fn in registry.get_by_category(cat):
            print(f"  {fn.name}")
            print(f"    {fn.description}")
            
            if fn.params:
                params = ", ".join(
                    f"{p.name}{'*' if p.required else ''}"
                    for p in fn.params
                )
                print(f"    Params: {params}")
            
            if fn.shell_template:
                print(f"    Shell: {fn.shell_template}")
            
            print()
    
    print("=" * 60)
    print("Use 'sq shell' for interactive mode with LLM understanding")
    print("=" * 60)
    
    return 0


def handle_accounting(args) -> int:
    """Handle accounting command - document scanning, OCR, invoices."""
    from .components.accounting import (
        AccountingComponent, AccountingProjectManager, 
        InteractiveScanner, get_available_engines,
        AutoScanner, VoiceAssistant, voice_summary, voice_ask
    )
    from .core import StreamwareURI
    
    operation = getattr(args, 'operation', 'interactive')
    project = getattr(args, 'project', 'default')
    source = getattr(args, 'source', 'camera')
    file_path = getattr(args, 'file', None)
    folder_path = getattr(args, 'folder', None)
    doc_type = getattr(args, 'type', 'auto')
    ocr_engine = getattr(args, 'ocr_engine', 'auto')
    lang = getattr(args, 'lang', 'pol')
    crop = not getattr(args, 'no_crop', False)
    tts = getattr(args, 'tts', False)
    export_format = getattr(args, 'format', 'csv')
    question = getattr(args, 'question', None)
    interval = getattr(args, 'interval', 2.0)
    preview = getattr(args, 'preview', False)
    confirm = getattr(args, 'confirm', False)
    
    if operation == 'watch':
        if not folder_path:
            folder_path = f"~/Documents/accounting/{project}"
            print(f"💡 Używam domyślnego folderu: {folder_path}")
        
        scanner = AutoScanner(project)
        scanner.watch_folder(folder_path, interval=interval, preview=preview, confirm=confirm)
        return 0
    
    elif operation == 'batch':
        if not folder_path:
            print("❌ Podaj folder: --folder /ścieżka/do/folderu", file=sys.stderr)
            return 1
        
        scanner = AutoScanner(project)
        scanner.batch_process(folder_path, preview=preview, confirm=confirm)
        return 0
    
    elif operation == 'auto':
        scanner = AutoScanner(project)
        scanner.continuous_scan(source=source, interval=interval, preview=preview, confirm=confirm)
        return 0
    
    elif operation == 'preview':
        from .accounting_web import run_opencv_preview
        camera_device = getattr(args, 'camera_device', 0)
        run_opencv_preview(source=source, camera_device=camera_device)
        return 0
    
    elif operation == 'web':
        from .accounting_web import run_accounting_web, load_camera_config_from_env, list_available_cameras
        port = int(getattr(args, 'port', 8088) or 8088)
        no_browser = getattr(args, 'no_browser', False)
        camera_device = getattr(args, 'camera_device', 0)
        rtsp_url = getattr(args, 'rtsp', None)
        camera_name = getattr(args, 'camera', None)
        
        if camera_name and not rtsp_url:
            env_config = load_camera_config_from_env()
            available = list_available_cameras(env_config)
            
            for cam in available:
                if cam["name"] == camera_name:
                    rtsp_url = cam["url"]
                    source = "rtsp"
                    break
            
            if not rtsp_url and camera_name.isdigit():
                idx = int(camera_name)
                if idx < len(available):
                    rtsp_url = available[idx]["url"]
                    source = "rtsp"
        
        if rtsp_url:
            source = "rtsp"
        
        doc_types = []
        if getattr(args, 'receipt', False):
            doc_types.append('receipt')
        if getattr(args, 'invoice', False):
            doc_types.append('invoice')
        if getattr(args, 'document', False):
            doc_types.append('document')
        
        detect_mode = getattr(args, 'detect_mode', 'auto')
        
        run_accounting_web(
            project=project, 
            port=port, 
            open_browser=not no_browser,
            source=source,
            camera_device=camera_device,
            rtsp_url=rtsp_url,
            doc_types=doc_types if doc_types else None,
            detect_mode=detect_mode
        )
        return 0
    
    elif operation == 'ask':
        if not question:
            assistant = VoiceAssistant()
            print("\n🎤 Asystent księgowy - zadaj pytanie (q=koniec)")
            print("   Przykłady: 'ile mam faktur?', 'jaka jest suma paragonów?'\n")
            
            while True:
                try:
                    q = input("❓ ").strip()
                    if q.lower() in ['q', 'quit', 'exit']:
                        break
                    if q:
                        answer = assistant.answer_question(q, project if project != 'default' else None)
                        print(f"📢 {answer}\n")
                        if tts:
                            assistant.speak_summary(project if project != 'default' else None)
                except (KeyboardInterrupt, EOFError):
                    break
            return 0
        else:
            answer = voice_ask(question, project if project != 'default' else None)
            print(f"📢 {answer}")
            if tts:
                VoiceAssistant().speak_summary(project if project != 'default' else None)
            return 0
    
    uri_str = f"accounting://{operation}?project={project}&source={source}&lang={lang}"
    uri_str += f"&ocr_engine={ocr_engine}&crop={'true' if crop else 'false'}"
    uri_str += f"&preview={'true' if preview else 'false'}&confirm={'true' if confirm else 'false'}"
    uri_str += f"&tts={'true' if tts else 'false'}&format={export_format}"
    
    if file_path:
        uri_str += f"&file={file_path}"
    if doc_type and doc_type != 'auto':
        uri_str += f"&type={doc_type}"
    
    try:
        uri = StreamwareURI(uri_str)
        component = AccountingComponent(uri)
        result = component.process(None)
        
        if operation == 'engines':
            print("\n🔧 Dostępne silniki OCR:")
            print("-" * 40)
            for engine in result.get('engines', []):
                status = "✅" if engine['available'] else "❌"
                print(f"  {status} {engine['name']}")
            print(f"\n  📌 Zalecany: {result.get('recommended', 'tesseract')}")
            
        elif operation == 'list':
            print("\n📁 Projekty księgowe:")
            print("-" * 40)
            for proj in result.get('projects', []):
                print(f"  📂 {proj['name']} ({proj['documents']} dokumentów)")
            
            summary = voice_summary()
            print(f"\n📢 {summary}")
                
        elif operation == 'summary':
            print(f"\n📊 Podsumowanie projektu: {project}")
            print("-" * 40)
            print(f"  📄 Dokumenty: {result.get('total_documents', 0)}")
            by_type = result.get('by_type', {})
            print(f"  📝 Faktury: {by_type.get('invoice', 0)}")
            print(f"  🧾 Paragony: {by_type.get('receipt', 0)}")
            amounts = result.get('total_amounts', {})
            print(f"  💰 Suma faktur: {amounts.get('invoices', 0):.2f} PLN")
            print(f"  💵 Suma paragonów: {amounts.get('receipts', 0):.2f} PLN")
            
            if tts:
                VoiceAssistant().speak_summary(project)
            
        elif operation == 'export':
            print(f"\n✅ Eksportowano do: {result.get('path', '')}")
            
        elif operation == 'create':
            proj = result.get('project', {})
            print(f"\n✅ Utworzono projekt: {proj.get('name', '')}")
            print(f"   Ścieżka: {proj.get('path', '')}")
            
        elif operation == 'scan' or operation == 'analyze':
            doc = result.get('document', result)
            print(f"\n✅ Dokument przetworzony")
            print(f"   📄 Typ: {doc.get('document_type', doc.get('type', 'unknown'))}")
            print(f"   🎯 Pewność OCR: {doc.get('confidence', 0):.0%}")
            if doc.get('extracted_data'):
                data = doc['extracted_data']
                if 'amounts' in data:
                    print(f"   💰 Kwota: {data['amounts'].get('gross', 'N/A')} PLN")
                elif 'total_amount' in data:
                    print(f"   💰 Suma: {data.get('total_amount', 'N/A')} PLN")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        
        return 0
        
    except Exception as e:
        print(f"❌ Błąd: {e}", file=sys.stderr)
        return 1
