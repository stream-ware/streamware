"""
Web CLI Module

Entry point functions for running the accounting web service.
"""

import time
from typing import List, Optional

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from .camera_utils import find_free_port


def run_opencv_preview(source: str = "screen", camera_device: int = 0):
    """
    Run OpenCV window preview without browser.
    Alternative for users who prefer native window over browser.
    """
    # Import here to avoid circular imports
    from .accounting_web import AccountingWebService
    
    if not HAS_CV2:
        print("❌ OpenCV nie jest zainstalowany. Zainstaluj: pip install opencv-python")
        return

    print("\n🎥 Podgląd na żywo (OpenCV)")
    print("-" * 40)
    print(f"   Źródło: {source}")
    if source == "camera":
        print(f"   Kamera: /dev/video{camera_device}")
    print(f"\n   Klawisze:")
    print(f"   [SPACE] - Zrób zrzut i analizuj")
    print(f"   [S] - Zapisz bieżącą klatkę")
    print(f"   [Q/ESC] - Zakończ")
    print("-" * 40)

    # Create temp service for capture methods
    service = AccountingWebService(
        project_name="preview", 
        port=9999,  # Not used
        open_browser=False,
        source=source,
        camera_device=camera_device
    )

    # Run diagnostics
    diag = service.run_diagnostics()
    service.print_diagnostics(diag)

    if source == "camera":
        if not diag.get("camera_available"):
            print("\n❌ Brak dostępnej kamery!")
            print("   Użyj: sq accounting preview --source screen")
            return

        # Use OpenCV VideoCapture for live camera feed
        cap = cv2.VideoCapture(camera_device)
        if not cap.isOpened():
            print(f"❌ Nie można otworzyć kamery {camera_device}")
            return

        print(f"\n✅ Kamera {camera_device} otwarta")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Błąd odczytu z kamery")
                break

            # Show frame
            cv2.imshow("Streamware Accounting Preview (Q=quit, SPACE=capture)", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):  # Q or ESC
                break
            elif key == ord(' '):  # SPACE - capture and analyze
                print("\n📸 Analiza klatki...")
                _, jpeg = cv2.imencode('.jpg', frame)
                analysis = service.analyze_frame(jpeg.tobytes())
                if analysis["detected"]:
                    print(f"   ✅ Wykryto: {analysis['doc_type']} ({analysis['confidence']:.0%})")
                else:
                    print("   ❌ Nie wykryto dokumentu")
            elif key == ord('s'):  # S - save frame
                filename = f"/tmp/scan_{int(time.time())}.jpg"
                cv2.imwrite(filename, frame)
                print(f"   💾 Zapisano: {filename}")

        cap.release()
        cv2.destroyAllWindows()

    else:  # screen
        print("\n📺 Podgląd ekranu (odświeżanie co 1s)")
        print("   Naciśnij Q lub ESC aby zakończyć\n")

        while True:
            image_bytes = service.capture_screen()
            if image_bytes:
                # Convert to OpenCV format
                nparr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Resize for display
                    h, w = frame.shape[:2]
                    max_width = 1280
                    if w > max_width:
                        scale = max_width / w
                        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

                    cv2.imshow("Streamware Accounting Preview (Q=quit, SPACE=capture)", frame)

            key = cv2.waitKey(1000) & 0xFF  # 1 second refresh
            if key in (ord('q'), 27):
                break
            elif key == ord(' '):
                if image_bytes:
                    print("\n📸 Analiza klatki...")
                    analysis = service.analyze_frame(image_bytes)
                    if analysis["detected"]:
                        print(f"   ✅ Wykryto: {analysis['doc_type']} ({analysis['confidence']:.0%})")
                    else:
                        print("   ❌ Nie wykryto dokumentu")

        cv2.destroyAllWindows()

    print("\n✅ Podgląd zakończony")


def run_accounting_web(project: str = "web_archive", port: int = 8088, open_browser: bool = True,
                       source: str = "screen", camera_device: int = 0, rtsp_url: str = None,
                       low_latency: bool = True, doc_types: List[str] = None, detect_mode: str = "auto"):
    """Start accounting web service.
    
    Args:
        doc_types: List of document types to detect ['receipt', 'invoice', 'document']
        detect_mode: Detection mode - 'fast', 'accurate', or 'auto'
    """
    # Import here to avoid circular imports
    from .accounting_web import AccountingWebService
    
    # Find free port if default is busy
    actual_port = find_free_port(port)
    if actual_port != port:
        print(f"⚠️  Port {port} zajęty, używam {actual_port}")

    # Show detection mode
    if doc_types:
        print(f"🎯 Tryb wykrywania: {', '.join(doc_types)} ({detect_mode})")
    
    service = AccountingWebService(
        project_name=project, 
        port=actual_port, 
        open_browser=open_browser,
        source=source,
        camera_device=camera_device,
        rtsp_url=rtsp_url,
        low_latency=low_latency,
        doc_types=doc_types,
        detect_mode=detect_mode
    )
    service.run()
