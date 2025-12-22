#!/usr/bin/env python3
"""
Process branding images to remove white backgrounds and convert to PNG.

Requirements:
    pip install pillow

Usage:
    python scripts/process_images.py
"""

from pathlib import Path
from PIL import Image
import numpy as np


def remove_white_background(image_path, output_path, threshold=240):
    """Remove white background from image and save as PNG with transparency."""
    print(f"Processing: {image_path.name}")

    # Open image
    img = Image.open(image_path).convert("RGBA")

    # Convert to numpy array
    data = np.array(img)

    # Get RGB channels
    r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]

    # Find white/light pixels (all RGB values above threshold)
    white_areas = (r > threshold) & (g > threshold) & (b > threshold)

    # Set alpha to 0 for white areas
    data[white_areas] = [0, 0, 0, 0]

    # Create new image
    result = Image.fromarray(data)

    # Save as PNG
    result.save(output_path, "PNG", optimize=True)
    print(f"  ✓ Saved to: {output_path}")

    return result


def crop_to_content(image_path, output_path, padding=20):
    """Crop image to content bounds with optional padding."""
    print(f"Cropping: {image_path.name}")

    # Open image
    img = Image.open(image_path).convert("RGBA")

    # Get bounding box of non-transparent pixels
    bbox = img.getbbox()

    if bbox:
        # Add padding
        bbox = (
            max(0, bbox[0] - padding),
            max(0, bbox[1] - padding),
            min(img.width, bbox[2] + padding),
            min(img.height, bbox[3] + padding)
        )

        # Crop to bbox
        img = img.crop(bbox)

    # Save
    img.save(output_path, "PNG", optimize=True)
    print(f"  ✓ Saved cropped image: {output_path}")

    return img


def process_all_images():
    """Process all branding images."""
    assets_dir = Path("docs/assets")

    if not assets_dir.exists():
        print("❌ docs/assets/ directory not found")
        return

    print("=" * 70)
    print("🎨 Image Processing")
    print("=" * 70)

    # Images to process
    images = [
        ("logo.jpg", "logo.png"),
        ("favicon.jpg", "favicon.png"),
        ("graph-hero.jpg", "graph-hero.png"),
        ("apple-touch-icon.jpg", "apple-touch-icon.png"),
    ]

    for input_name, output_name in images:
        input_path = assets_dir / input_name
        temp_path = assets_dir / f"temp_{output_name}"
        output_path = assets_dir / output_name

        if not input_path.exists():
            print(f"⚠️  {input_name} not found, skipping...")
            continue

        try:
            # Step 1: Remove white background
            remove_white_background(input_path, temp_path)

            # Step 2: Crop to content
            crop_to_content(temp_path, output_path, padding=0)

            # Clean up temp file
            temp_path.unlink()

            print()
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            if temp_path.exists():
                temp_path.unlink()
            continue

    print("=" * 70)
    print("✅ Image processing complete!")
    print("=" * 70)
    print("\nProcessed files:")
    for _, output_name in images:
        output_path = assets_dir / output_name
        if output_path.exists():
            size_kb = output_path.stat().st_size / 1024
            print(f"  - {output_name} ({size_kb:.1f} KB)")

    print("\nNext steps:")
    print("  1. Review processed images")
    print("  2. Update mkdocs.yml to use .png files")
    print("  3. Update docs/index.md if needed")
    print("  4. Commit and deploy")


if __name__ == "__main__":
    try:
        import numpy
        from PIL import Image
    except ImportError:
        print("❌ Required packages not installed")
        print("   Run: pip install pillow numpy")
        exit(1)

    process_all_images()
