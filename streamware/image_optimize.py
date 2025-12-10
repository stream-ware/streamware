"""
Image Optimization for LLM Vision Processing

Optimizes images before sending to vision LLMs (LLaVA, GPT-4V) to reduce:
- Transfer size (faster API calls)
- LLM processing time
- Token usage (for API-based models)

Techniques:
- Downscaling to max dimensions (preserves aspect ratio)
- JPEG compression with configurable quality
- Optional posterization (color quantization)
- Optional grayscale conversion
- Edge-enhanced mode for motion regions

Usage:
    from streamware.image_optimize import prepare_image_for_llm, OptimizeConfig

    # Default optimization (recommended)
    optimized_path = prepare_image_for_llm(frame_path)

    # Custom config
    config = OptimizeConfig(max_size=512, quality=60, posterize_colors=16)
    optimized_path = prepare_image_for_llm(frame_path, config=config)

    # Get base64 directly
    image_b64 = prepare_image_for_llm_base64(frame_path)
"""

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple, Union
import base64

logger = logging.getLogger(__name__)


@dataclass
class OptimizeConfig:
    """Configuration for image optimization before LLM processing.

    Attributes:
        max_size: Maximum dimension (width or height). Image will be downscaled
                  proportionally if larger. Default 512 is a good balance.
        quality: JPEG quality (1-100). Lower = smaller file. 65 is good for LLM.
        posterize_colors: If > 0, reduce to this many colors (8-256).
                          Reduces complexity while preserving shapes.
        grayscale: Convert to grayscale. Reduces data 3x but may hurt
                   color-dependent detection. Generally NOT recommended for LLM.
        sharpen: Apply sharpening to preserve edges after downscaling.
        denoise: Apply light denoising to reduce artifacts.
        edge_enhance: Enhance edges for better object detection.
    """
    max_size: int = 512
    quality: int = 65
    posterize_colors: int = 0  # 0 = disabled, 8-256 = quantize
    grayscale: bool = False
    sharpen: bool = True
    denoise: bool = False
    edge_enhance: bool = False


# Preset configurations
PRESETS = {
    "fast": OptimizeConfig(max_size=384, quality=55, posterize_colors=32, sharpen=False),
    "balanced": OptimizeConfig(max_size=512, quality=65, posterize_colors=0, sharpen=True),
    "quality": OptimizeConfig(max_size=768, quality=75, posterize_colors=0, sharpen=True),
    "minimal": OptimizeConfig(max_size=256, quality=50, posterize_colors=16, grayscale=True),
}


def get_config_from_env() -> OptimizeConfig:
    """Load optimization config from environment / .env file.

    Uses SQ_IMAGE_* variables if set, otherwise returns balanced preset.
    """
    try:
        from .config import config as sq_config

        preset_name = sq_config.get("SQ_IMAGE_PRESET", "balanced")
        if preset_name in PRESETS and not any([
            sq_config.get("SQ_IMAGE_MAX_SIZE"),
            sq_config.get("SQ_IMAGE_QUALITY"),
            sq_config.get("SQ_IMAGE_POSTERIZE"),
            sq_config.get("SQ_IMAGE_GRAYSCALE"),
        ]):
            # Use preset if no custom values set
            return PRESETS[preset_name]

        # Build custom config from env
        return OptimizeConfig(
            max_size=int(sq_config.get("SQ_IMAGE_MAX_SIZE", "512")),
            quality=int(sq_config.get("SQ_IMAGE_QUALITY", "65")),
            posterize_colors=int(sq_config.get("SQ_IMAGE_POSTERIZE", "0")),
            grayscale=sq_config.get("SQ_IMAGE_GRAYSCALE", "false").lower() == "true",
            sharpen=True,
        )
    except Exception:
        return PRESETS["balanced"]


def prepare_image_for_llm(
    image_path: Union[str, Path],
    config: Optional[OptimizeConfig] = None,
    preset: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """Prepare image for LLM vision processing.

    Args:
        image_path: Path to source image
        config: OptimizeConfig instance (overrides preset and env)
        preset: One of "fast", "balanced", "quality", "minimal".
                If None, uses SQ_IMAGE_PRESET from .env or defaults to "balanced".
        output_path: Where to save optimized image. If None, uses temp file.

    Returns:
        Path to optimized image (JPEG)
    """
    try:
        from PIL import Image, ImageFilter, ImageOps, ImageEnhance
    except ImportError:
        logger.warning("PIL not installed, returning original image")
        return Path(image_path)

    if config is None:
        if preset is not None:
            config = PRESETS.get(preset, PRESETS["balanced"])
        else:
            # Use config from .env
            config = get_config_from_env()

    try:
        img = Image.open(image_path)

        # Convert to RGB if necessary (handle RGBA, P mode, etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # 1. Downscale if larger than max_size
        if max(img.size) > config.max_size:
            img = _downscale(img, config.max_size)

        # 2. Grayscale conversion (optional)
        if config.grayscale:
            img = img.convert("L")

        # 3. Posterization / color quantization (optional)
        if config.posterize_colors > 0 and img.mode != "L":
            img = _posterize(img, config.posterize_colors)

        # 4. Denoise (optional)
        if config.denoise:
            img = img.filter(ImageFilter.MedianFilter(size=3))

        # 5. Sharpen (optional, helps after downscaling)
        if config.sharpen:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.3)

        # 6. Edge enhance (optional)
        if config.edge_enhance:
            img = img.filter(ImageFilter.EDGE_ENHANCE)

        # Save optimized image
        if output_path is None:
            fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
            import os
            os.close(fd)
            output_path = Path(tmp_path)

        # Ensure RGB for JPEG save
        if img.mode == "L":
            img.save(output_path, "JPEG", quality=config.quality, optimize=True)
        else:
            img = img.convert("RGB")
            img.save(output_path, "JPEG", quality=config.quality, optimize=True)

        return output_path

    except Exception as e:
        logger.warning(f"Image optimization failed: {e}, using original")
        return Path(image_path)


def prepare_image_for_llm_base64(
    image_path: Union[str, Path],
    config: Optional[OptimizeConfig] = None,
    preset: str = "balanced",
) -> str:
    """Prepare image and return as base64 string for LLM API.

    Args:
        image_path: Path to source image
        config: OptimizeConfig instance
        preset: Preset name if config not provided

    Returns:
        Base64-encoded optimized JPEG
    """
    optimized_path = prepare_image_for_llm(image_path, config=config, preset=preset)
    try:
        with open(optimized_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    finally:
        # Cleanup temp file if we created one
        if optimized_path != Path(image_path):
            try:
                optimized_path.unlink()
            except Exception:
                pass


def get_image_stats(image_path: Union[str, Path]) -> dict:
    """Get image statistics for debugging/logging.

    Returns:
        Dict with size, dimensions, format, estimated LLM tokens
    """
    try:
        from PIL import Image
        import os

        img = Image.open(image_path)
        file_size = os.path.getsize(image_path)

        # Rough token estimation for vision models
        # GPT-4V: ~85 tokens per 512x512 tile
        tiles = (img.width // 512 + 1) * (img.height // 512 + 1)
        estimated_tokens = tiles * 85

        return {
            "width": img.width,
            "height": img.height,
            "mode": img.mode,
            "format": img.format,
            "file_size_kb": round(file_size / 1024, 1),
            "estimated_tokens": estimated_tokens,
        }
    except Exception as e:
        return {"error": str(e)}


def _downscale(img: 'Image.Image', max_size: int) -> 'Image.Image':
    """Downscale image proportionally to fit within max_size."""
    from PIL import Image
    
    width, height = img.size
    if width > height:
        new_width = max_size
        new_height = int(height * (max_size / width))
    else:
        new_height = max_size
        new_width = int(width * (max_size / height))

    # Use LANCZOS for high-quality downscaling
    return img.resize((new_width, new_height), Image.LANCZOS)


def _posterize(img: 'Image.Image', num_colors: int) -> 'Image.Image':
    """Reduce image to specified number of colors.

    Uses quantization which preserves visual structure while reducing complexity.
    """
    from PIL import Image
    
    try:
        # Convert to palette mode with limited colors, then back to RGB
        return img.quantize(colors=num_colors, method=Image.MEDIANCUT).convert("RGB")
    except Exception:
        return img


def compare_optimization(image_path: Union[str, Path]) -> dict:
    """Compare original vs optimized image stats.

    Useful for tuning optimization parameters.
    """
    original_stats = get_image_stats(image_path)

    results = {"original": original_stats}

    for preset_name, config in PRESETS.items():
        optimized_path = prepare_image_for_llm(image_path, config=config)
        try:
            results[preset_name] = get_image_stats(optimized_path)
            # Cleanup
            if optimized_path != Path(image_path):
                optimized_path.unlink()
        except Exception as e:
            results[preset_name] = {"error": str(e)}

    return results
