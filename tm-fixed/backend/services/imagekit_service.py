from imagekitio import ImageKit

from backend.config import IMAGEKIT_PRIVATE_KEY, IMAGEKIT_URL_ENDPOINT

# Only private_key is needed for server-side uploads.
# The SDK reads IMAGEKIT_PRIVATE_KEY from env automatically, but we pass it
# explicitly so it still works when config.py loads from a .env file.
imagekit = ImageKit(private_key=IMAGEKIT_PRIVATE_KEY)


def upload_image(
    file_bytes: bytes,
    file_name: str,
    folder: str,
    content_type: str = "image/png",
) -> str:
    """Upload raw bytes to ImageKit and return the CDN URL."""
    result = imagekit.files.upload(
        # SDK FileTypes accepts (filename, bytes, content_type)
        file=(file_name, file_bytes, content_type),
        file_name=file_name,
        folder=folder,
        is_private_file=False,
        use_unique_file_name=True,
    )
    if not result.url:
        raise RuntimeError(f"ImageKit upload succeeded but returned no URL: {result}")
    return result.url


def get_variants(base_url: str) -> dict:
    """Return ImageKit transformation URLs for the three thumbnail formats."""
    return {
        "youtube": f"{base_url}?tr=w-1280,h-720,c-maintain_ratio,fo-auto",
        "shorts":  f"{base_url}?tr=w-1080,h-1920,c-maintain_ratio,fo-auto",
        "square":  f"{base_url}?tr=w-1080,h-1080,c-maintain_ratio,fo-auto",
    }
