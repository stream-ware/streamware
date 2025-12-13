"""
Scanner Performance Tests

Tests for document detection performance, bottleneck identification,
and system efficiency.
"""

import time
import numpy as np
import pytest
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class TestDetectionPerformance:
    """Test detection speed and accuracy."""
    
    @pytest.fixture
    def sample_frame(self):
        """Create a sample frame for testing."""
        if not HAS_CV2:
            pytest.skip("OpenCV not available")
        # Create a white rectangle on dark background (simulates document)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(frame, (100, 50), (540, 430), (255, 255, 255), -1)
        # Add some text-like horizontal lines
        for y in range(80, 400, 20):
            cv2.line(frame, (120, y), (520, y), (50, 50, 50), 1)
        return frame
    
    @pytest.fixture
    def receipt_frame(self):
        """Create a receipt-like frame (tall narrow)."""
        if not HAS_CV2:
            pytest.skip("OpenCV not available")
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Tall narrow white rectangle
        cv2.rectangle(frame, (220, 20), (420, 460), (255, 255, 255), -1)
        for y in range(40, 440, 15):
            cv2.line(frame, (230, y), (410, y), (30, 30, 30), 1)
        return frame

    def test_receipt_detector_speed(self, receipt_frame):
        """Test receipt detection speed."""
        from streamware.document_detectors import ReceiptDetector
        
        detector = ReceiptDetector()
        
        # Warmup
        detector.detect(receipt_frame)
        
        # Measure
        times = []
        for _ in range(10):
            t_start = time.time()
            result = detector.detect(receipt_frame)
            times.append((time.time() - t_start) * 1000)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        print(f"\n--- Receipt Detector Performance ---")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")
        print(f"  Detected: {result['detected']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Features: {result.get('features', [])}")
        
        # Performance assertions
        assert avg_time < 50, f"Receipt detection too slow: {avg_time:.2f}ms"
        assert result['detected'], "Should detect receipt-like shape"
        assert result['confidence'] > 0.3, "Confidence should be > 0.3"

    def test_invoice_detector_speed(self, sample_frame):
        """Test invoice detection speed."""
        from streamware.document_detectors import InvoiceDetector
        
        detector = InvoiceDetector()
        
        times = []
        for _ in range(10):
            t_start = time.time()
            result = detector.detect(sample_frame)
            times.append((time.time() - t_start) * 1000)
        
        avg_time = sum(times) / len(times)
        
        print(f"\n--- Invoice Detector Performance ---")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Detected: {result['detected']}")
        
        assert avg_time < 50, f"Invoice detection too slow: {avg_time:.2f}ms"

    def test_general_detector_speed(self, sample_frame):
        """Test general document detection speed."""
        from streamware.document_detectors import GeneralDocumentDetector
        
        detector = GeneralDocumentDetector()
        
        times = []
        for _ in range(10):
            t_start = time.time()
            result = detector.detect(sample_frame)
            times.append((time.time() - t_start) * 1000)
        
        avg_time = sum(times) / len(times)
        
        print(f"\n--- General Detector Performance ---")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Detected: {result['detected']}")
        
        assert avg_time < 30, f"General detection too slow: {avg_time:.2f}ms"

    def test_detector_manager_speed(self, receipt_frame):
        """Test full detection pipeline speed."""
        from streamware.document_detectors import DocumentDetectorManager
        
        manager = DocumentDetectorManager(doc_types=['receipt', 'invoice', 'document'])
        
        times = []
        for _ in range(10):
            t_start = time.time()
            result = manager.detect(receipt_frame)
            times.append((time.time() - t_start) * 1000)
        
        avg_time = sum(times) / len(times)
        
        print(f"\n--- Detector Manager Performance ---")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Detected: {result['detected']}")
        print(f"  Method: {result.get('method')}")
        print(f"  Timing breakdown: {result.get('timing', {})}")
        
        assert avg_time < 100, f"Detection pipeline too slow: {avg_time:.2f}ms"


class TestClassifierPerformance:
    """Test LLM classifier performance."""
    
    def test_fallback_classifier_speed(self):
        """Test fallback (non-LLM) classification speed."""
        from streamware.document_classifier import DocumentClassifier
        
        classifier = DocumentClassifier()
        classifier.enabled = False  # Force fallback mode
        
        sample_text = """
        PARAGON FISKALNY
        BIEDRONKA Sp. z o.o.
        NIP: 123-456-78-90
        Data: 2024-01-15
        
        Chleb         3.50 zł
        Mleko         4.20 zł
        Masło         7.80 zł
        
        SUMA: 15.50 zł
        Gotówka: 20.00 zł
        Reszta: 4.50 zł
        """
        
        times = []
        for _ in range(100):
            t_start = time.time()
            result = classifier._fallback_classify(sample_text)
            times.append((time.time() - t_start) * 1000)
        
        avg_time = sum(times) / len(times)
        
        print(f"\n--- Fallback Classifier Performance ---")
        print(f"  Average: {avg_time:.3f}ms")
        print(f"  Result: {result}")
        
        assert avg_time < 1, f"Fallback classification too slow: {avg_time:.3f}ms"
        assert result['document_type'] == 'receipt', "Should detect as receipt"


class TestConfigLoading:
    """Test configuration loading performance."""
    
    def test_config_load_speed(self):
        """Test configuration loading speed."""
        from streamware.scanner_config import ScannerConfig
        
        times = []
        for _ in range(10):
            t_start = time.time()
            config = ScannerConfig()
            times.append((time.time() - t_start) * 1000)
        
        avg_time = sum(times) / len(times)
        
        print(f"\n--- Config Loading Performance ---")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  FPS: {config.fps}")
        print(f"  LLM model: {config.llm_model}")
        
        assert avg_time < 100, f"Config loading too slow: {avg_time:.2f}ms"


class TestBottleneckDetection:
    """Identify performance bottlenecks."""
    
    def test_identify_bottlenecks(self):
        """Run full pipeline and identify bottlenecks."""
        if not HAS_CV2:
            pytest.skip("OpenCV not available")
        
        from streamware.document_detectors import DocumentDetectorManager
        
        # Create test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(frame, (100, 50), (540, 430), (255, 255, 255), -1)
        
        manager = DocumentDetectorManager()
        result = manager.detect(frame)
        
        timing = result.get('timing', {})
        total = timing.get('total', 0)
        
        print(f"\n--- Bottleneck Analysis ---")
        print(f"  Total time: {total:.2f}ms")
        
        bottlenecks = []
        for step, time_ms in timing.items():
            if step == 'total':
                continue
            pct = (time_ms / total * 100) if total > 0 else 0
            print(f"  {step}: {time_ms:.2f}ms ({pct:.1f}%)")
            if pct > 50:
                bottlenecks.append((step, time_ms, pct))
        
        if bottlenecks:
            print(f"\n  ⚠️ Bottlenecks detected:")
            for step, time_ms, pct in bottlenecks:
                print(f"    - {step}: {time_ms:.2f}ms ({pct:.1f}%)")
        else:
            print(f"\n  ✅ No significant bottlenecks")


def run_all_tests():
    """Run all performance tests and generate YAML report."""
    import yaml
    
    results = {
        "test_run": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "tests": []
        }
    }
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
    
    print("\n" + "="*50)
    print("Performance Test Summary")
    print("="*50)


if __name__ == "__main__":
    run_all_tests()
