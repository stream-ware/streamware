"""
Animal Detector for Streamware

Specialized detection for animals using YOLO.
Optimized for birds, cats, dogs, and wildlife.

Features:
- Fast bird detection (feeders, gardens)
- Pet monitoring (cats, dogs)
- Wildlife tracking
- Size-based filtering (ignore small movements)
- Behavior classification

Usage:
    from streamware.animal_detector import AnimalDetector
    
    detector = AnimalDetector(focus="bird")
    result = detector.detect(frame_path)
    
    for animal in result.animals:
        print(f"{animal.species}: {animal.behavior} at {animal.position}")
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AnimalSpecies(Enum):
    """Supported animal species."""
    # Birds
    BIRD = "bird"
    
    # Pets
    DOG = "dog"
    CAT = "cat"
    
    # Farm animals
    HORSE = "horse"
    COW = "cow"
    SHEEP = "sheep"
    
    # Wildlife
    BEAR = "bear"
    ELEPHANT = "elephant"
    ZEBRA = "zebra"
    GIRAFFE = "giraffe"
    
    # Generic
    ANIMAL = "animal"
    UNKNOWN = "unknown"


class AnimalBehavior(Enum):
    """Animal behavior states."""
    STATIONARY = "stationary"
    MOVING = "moving"
    FLYING = "flying"
    EATING = "eating"
    RESTING = "resting"
    PLAYING = "playing"
    ALERT = "alert"
    UNKNOWN = "unknown"


# YOLO class IDs for animals (COCO dataset)
ANIMAL_CLASSES = {
    14: AnimalSpecies.BIRD,
    15: AnimalSpecies.CAT,
    16: AnimalSpecies.DOG,
    17: AnimalSpecies.HORSE,
    18: AnimalSpecies.SHEEP,
    19: AnimalSpecies.COW,
    20: AnimalSpecies.ELEPHANT,
    21: AnimalSpecies.BEAR,
    22: AnimalSpecies.ZEBRA,
    23: AnimalSpecies.GIRAFFE,
}

# Reverse mapping
SPECIES_TO_CLASS_ID = {v: k for k, v in ANIMAL_CLASSES.items()}


@dataclass
class DetectedAnimal:
    """A detected animal."""
    species: AnimalSpecies
    confidence: float
    
    # Position (normalized 0-1)
    x: float
    y: float
    w: float
    h: float
    
    # Pixel coordinates
    x_px: int = 0
    y_px: int = 0
    w_px: int = 0
    h_px: int = 0
    
    # Tracking
    track_id: int = 0
    behavior: AnimalBehavior = AnimalBehavior.UNKNOWN
    
    # Position description
    position: str = ""  # "left", "center", "right", "top", "bottom"
    
    @property
    def area(self) -> float:
        return self.w * self.h
    
    @property
    def is_small(self) -> bool:
        """Check if detection is very small (might be noise)."""
        return self.area < 0.005  # Less than 0.5% of frame
    
    def get_description(self) -> str:
        """Get human-readable description."""
        species_name = self.species.value.title()
        behavior_str = self.behavior.value if self.behavior != AnimalBehavior.UNKNOWN else ""
        
        if behavior_str:
            return f"{species_name} {behavior_str} in {self.position}"
        else:
            return f"{species_name} detected in {self.position}"


@dataclass
class AnimalDetectionResult:
    """Result of animal detection."""
    animals: List[DetectedAnimal] = field(default_factory=list)
    
    # Counts by species
    bird_count: int = 0
    cat_count: int = 0
    dog_count: int = 0
    other_count: int = 0
    
    # Timing
    detection_ms: float = 0.0
    
    # Frame info
    frame_path: str = ""
    timestamp: float = 0.0
    
    @property
    def total_count(self) -> int:
        return len(self.animals)
    
    @property
    def has_animals(self) -> bool:
        return len(self.animals) > 0
    
    @property
    def has_birds(self) -> bool:
        return self.bird_count > 0
    
    def get_summary(self) -> str:
        """Get summary of detections."""
        if not self.animals:
            return "No animals detected"
        
        parts = []
        if self.bird_count > 0:
            parts.append(f"{self.bird_count} bird{'s' if self.bird_count > 1 else ''}")
        if self.cat_count > 0:
            parts.append(f"{self.cat_count} cat{'s' if self.cat_count > 1 else ''}")
        if self.dog_count > 0:
            parts.append(f"{self.dog_count} dog{'s' if self.dog_count > 1 else ''}")
        if self.other_count > 0:
            parts.append(f"{self.other_count} other animal{'s' if self.other_count > 1 else ''}")
        
        return ", ".join(parts) + " detected"
    
    def get_detailed_summary(self) -> str:
        """Get detailed summary with positions."""
        if not self.animals:
            return "No animals detected"
        
        descriptions = [a.get_description() for a in self.animals[:5]]  # Max 5
        return ". ".join(descriptions)


class AnimalDetector:
    """
    Specialized animal detector using YOLO.
    
    Optimized for:
    - Bird feeders / garden monitoring
    - Pet cameras
    - Wildlife cameras
    """
    
    def __init__(
        self,
        focus: str = "all",  # "all", "bird", "cat", "dog", "wildlife"
        model: str = "yolov8n",
        confidence_threshold: float = 0.3,
        min_size: float = 0.003,  # Minimum detection size (3% of frame)
        device: str = "auto",
    ):
        """
        Initialize animal detector.
        
        Args:
            focus: What to detect ("all", "bird", "cat", "dog", "wildlife")
            model: YOLO model name
            confidence_threshold: Minimum confidence
            min_size: Minimum detection size (normalized)
            device: Device to use
        """
        self.focus = focus
        self.model_name = model
        self.confidence_threshold = confidence_threshold
        self.min_size = min_size
        self.device = device
        
        self._yolo = None
        self._initialized = False
        
        # Track history for behavior detection
        self._track_history: Dict[int, List[Tuple[float, float, float]]] = {}
    
    def _get_class_filter(self) -> List[int]:
        """Get YOLO class IDs to detect based on focus."""
        if self.focus == "all":
            return list(ANIMAL_CLASSES.keys())
        elif self.focus == "bird":
            return [14]  # Bird only
        elif self.focus == "cat":
            return [15]  # Cat only
        elif self.focus == "dog":
            return [16]  # Dog only
        elif self.focus == "pet":
            return [15, 16]  # Cat + Dog
        elif self.focus == "wildlife":
            return [17, 18, 19, 20, 21, 22, 23]  # Farm + wild animals
        else:
            return list(ANIMAL_CLASSES.keys())
    
    def _init_yolo(self) -> bool:
        """Initialize YOLO detector."""
        if self._initialized:
            return True
        
        try:
            from .yolo_detector import ensure_yolo_available, YOLODetector
            
            if not ensure_yolo_available(verbose=True):
                logger.warning("YOLO not available for animal detection")
                return False
            
            class_filter = self._get_class_filter()
            
            self._yolo = YOLODetector(
                model=self.model_name,
                confidence_threshold=self.confidence_threshold,
            )
            # Override class filter for animals
            self._yolo.class_filter = class_filter
            
            self._initialized = True
            logger.info(f"Animal detector initialized: {self.focus} focus, classes={class_filter}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize animal detector: {e}")
            return False
    
    def detect(self, frame_path: Path) -> AnimalDetectionResult:
        """
        Detect animals in frame.
        
        Args:
            frame_path: Path to image file
            
        Returns:
            AnimalDetectionResult with all detected animals
        """
        result = AnimalDetectionResult(
            frame_path=str(frame_path),
            timestamp=time.time(),
        )
        
        if not self._init_yolo():
            return result
        
        start = time.time()
        
        try:
            # Run YOLO detection
            detections = self._yolo.detect(frame_path)
            result.detection_ms = (time.time() - start) * 1000
            
            for det in detections:
                # Get species from class ID
                class_id = det.class_id
                species = ANIMAL_CLASSES.get(class_id, AnimalSpecies.UNKNOWN)
                
                if species == AnimalSpecies.UNKNOWN:
                    continue
                
                # Create detected animal
                animal = DetectedAnimal(
                    species=species,
                    confidence=det.confidence,
                    x=det.x,
                    y=det.y,
                    w=det.w,
                    h=det.h,
                    x_px=det.x_px,
                    y_px=det.y_px,
                    w_px=det.w_px,
                    h_px=det.h_px,
                )
                
                # Skip very small detections (noise)
                if animal.area < self.min_size:
                    continue
                
                # Determine position
                animal.position = self._get_position(det.x, det.y)
                
                # Detect behavior (simple for now)
                animal.behavior = self._detect_behavior(animal)
                
                result.animals.append(animal)
                
                # Update counts
                if species == AnimalSpecies.BIRD:
                    result.bird_count += 1
                elif species == AnimalSpecies.CAT:
                    result.cat_count += 1
                elif species == AnimalSpecies.DOG:
                    result.dog_count += 1
                else:
                    result.other_count += 1
            
        except Exception as e:
            logger.error(f"Animal detection failed: {e}")
        
        return result
    
    def _get_position(self, x: float, y: float) -> str:
        """Get position description from coordinates."""
        h_pos = "center"
        if x < 0.33:
            h_pos = "left"
        elif x > 0.66:
            h_pos = "right"
        
        v_pos = ""
        if y < 0.33:
            v_pos = "top "
        elif y > 0.66:
            v_pos = "bottom "
        
        return f"{v_pos}{h_pos}".strip()
    
    def _detect_behavior(self, animal: DetectedAnimal) -> AnimalBehavior:
        """Detect animal behavior based on position and movement."""
        # Simple behavior detection based on species and position
        
        if animal.species == AnimalSpecies.BIRD:
            # Birds at top of frame might be flying
            if animal.y < 0.3 and animal.h < 0.1:
                return AnimalBehavior.FLYING
            # Birds at feeders usually eating
            elif animal.y > 0.5:
                return AnimalBehavior.EATING
            else:
                return AnimalBehavior.STATIONARY
        
        elif animal.species in (AnimalSpecies.CAT, AnimalSpecies.DOG):
            # Low position might be resting
            if animal.y > 0.7 and animal.h < 0.15:
                return AnimalBehavior.RESTING
            else:
                return AnimalBehavior.STATIONARY
        
        return AnimalBehavior.UNKNOWN


class BirdFeederMonitor:
    """
    Specialized monitor for bird feeders.
    
    Features:
    - Bird counting
    - Species-like size classification (small/medium/large birds)
    - Activity tracking (arrivals, departures)
    - Peak activity times
    """
    
    def __init__(
        self,
        model: str = "yolov8n",
        confidence_threshold: float = 0.25,
    ):
        self.detector = AnimalDetector(
            focus="bird",
            model=model,
            confidence_threshold=confidence_threshold,
            min_size=0.001,  # Smaller threshold for birds
        )
        
        # Statistics
        self.total_visits = 0
        self.current_count = 0
        self.max_count = 0
        self.activity_log: List[Dict] = []
    
    def update(self, frame_path: Path) -> Dict:
        """
        Update with new frame.
        
        Returns:
            Dict with current state and events
        """
        result = self.detector.detect(frame_path)
        
        prev_count = self.current_count
        self.current_count = result.bird_count
        
        events = []
        
        # Detect arrivals
        if self.current_count > prev_count:
            arrivals = self.current_count - prev_count
            events.append(f"{arrivals} bird{'s' if arrivals > 1 else ''} arrived")
            self.total_visits += arrivals
        
        # Detect departures
        elif self.current_count < prev_count:
            departures = prev_count - self.current_count
            events.append(f"{departures} bird{'s' if departures > 1 else ''} left")
        
        # Update max
        if self.current_count > self.max_count:
            self.max_count = self.current_count
            events.append(f"New record: {self.max_count} birds at once!")
        
        # Log activity
        if result.has_birds:
            self.activity_log.append({
                "timestamp": result.timestamp,
                "count": self.current_count,
                "positions": [a.position for a in result.animals],
            })
        
        return {
            "current_count": self.current_count,
            "total_visits": self.total_visits,
            "max_count": self.max_count,
            "events": events,
            "summary": result.get_summary(),
            "details": result.get_detailed_summary(),
        }


def get_animal_detector(focus: str = "all") -> AnimalDetector:
    """Get animal detector for specified focus."""
    return AnimalDetector(focus=focus)


def get_bird_monitor() -> BirdFeederMonitor:
    """Get bird feeder monitor."""
    return BirdFeederMonitor()
