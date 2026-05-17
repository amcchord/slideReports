"""
Image optimization helpers for shrinking screenshots before embedding them
into emailed reports. Uses Pillow to downscale and re-encode as JPEG.
"""
import io
import logging
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)


# MIME types we should never try to "optimize". SVGs are vector and re-encoding
# would rasterize them; logos are small and benefit nothing from compression.
_SKIP_MIME_TYPES = {'image/svg+xml'}


def is_logo_src(src_url: str) -> bool:
    """
    Heuristic: detect logo/static image sources that we should not resize.

    Args:
        src_url: The original src attribute value from the rendered HTML.

    Returns:
        True if the source looks like a local logo / static asset.
    """
    if not src_url:
        return False
    # The custom_logo_base64 preference is inlined as a data: URL already.
    if src_url.startswith('data:'):
        return True
    # Local static assets (logo lives at /static/img/logo.png)
    if src_url.startswith('/static/'):
        return True
    return False


def optimize_image_bytes(
    data: bytes,
    *,
    max_width: int,
    jpeg_quality: int,
    source_mime: str,
) -> Tuple[bytes, str]:
    """
    Resize and recompress an image to keep email attachments small.

    Behavior:
    - SVGs are returned unchanged (vector format, no benefit from raster ops).
    - Images wider than ``max_width`` are downscaled with Lanczos resampling.
    - All raster images are re-encoded as JPEG at ``jpeg_quality`` with
      progressive encoding and optimization enabled.
    - Any failure (decode error, unknown format, etc.) returns the original
      bytes/mime so the report never breaks because of optimization.

    Args:
        data: Raw image bytes.
        max_width: Maximum width in pixels. Images at or below this width
            are not resized (but may still be re-encoded).
        jpeg_quality: JPEG quality (1-95).
        source_mime: Original MIME type, used to short-circuit SVGs.

    Returns:
        Tuple of (optimized_bytes, mime_type). On any error, falls back to
        (data, source_mime).
    """
    if source_mime in _SKIP_MIME_TYPES:
        return data, source_mime

    try:
        original_size = len(data)
        with Image.open(io.BytesIO(data)) as img:
            img.load()

            if img.width > max_width:
                new_height = max(1, int(img.height * (max_width / img.width)))
                img = img.resize((max_width, new_height), Image.LANCZOS)

            # JPEG can't store alpha; flatten onto white if needed.
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                alpha = img.split()[-1]
                background.paste(img, mask=alpha)
                img = background
            elif img.mode == 'P':
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            buf = io.BytesIO()
            img.save(
                buf,
                format='JPEG',
                quality=jpeg_quality,
                optimize=True,
                progressive=True,
            )
            new_bytes = buf.getvalue()

        # If optimization somehow made it larger (rare, but possible for very
        # small images), keep the original to avoid wasted bytes.
        if len(new_bytes) >= original_size and source_mime == 'image/jpeg':
            return data, source_mime

        return new_bytes, 'image/jpeg'

    except Exception as e:
        logger.warning(
            "Image optimization failed (mime=%s, size=%d bytes): %s; "
            "using original",
            source_mime, len(data), e,
        )
        return data, source_mime
