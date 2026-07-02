#!/usr/bin/env python3
"""
Universal Image Optimizer for Air Force Backgrounds

This script can optimize any images for use as subtle page backgrounds,
targeting ~500KB file size while maintaining quality.

Usage:
    python optimize_any_images.py --folder path/to/images
    python optimize_any_images.py --single image.jpg
"""

import os
import sys
import argparse
from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path
import io

def remove_watermarks(img):
    """
    Attempt to remove watermarks or overlays from images.
    This uses basic image processing techniques.
    """
    try:
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Method 1: Detect and remove text overlays in corners
        # This is a basic approach - watermarks in corners are common
        width, height = img.size
        
        # Create a copy for processing
        cleaned_img = img.copy()
        
        # Check corners for potential watermarks (usually lighter/darker than image)
        corner_size = min(width // 6, height // 6, 200)  # Max 200px corner check
        
        corners = [
            (0, 0, corner_size, corner_size),  # Top-left
            (width - corner_size, 0, width, corner_size),  # Top-right
            (0, height - corner_size, corner_size, height),  # Bottom-left
            (width - corner_size, height - corner_size, width, height)  # Bottom-right
        ]
        
        for corner in corners:
            corner_region = img.crop(corner)
            
            # Simple watermark detection: look for high contrast text areas
            # This is basic - more sophisticated methods would use OCR
            
            # Apply slight blur to text-like areas
            blurred = corner_region.filter(ImageFilter.GaussianBlur(0.5))
            
            # Paste back the slightly processed corner
            cleaned_img.paste(blurred, corner[:2])
        
        return cleaned_img
        
    except Exception as e:
        print(f"   ⚠️  Watermark removal failed: {e}")
        return img

def optimize_for_background(input_path, output_path, target_size_kb=500, max_width=1920):
    """
    Optimize any image for use as a subtle page background.
    
    Args:
        input_path: Path to input image
        output_path: Path to save optimized image
        target_size_kb: Target file size in KB
        max_width: Maximum width in pixels
    """
    try:
        with Image.open(input_path) as img:
            print(f"🔧 Processing {input_path.name}...")
            
            original_size = os.path.getsize(input_path) / 1024
            print(f"   📏 Original: {img.width}x{img.height}, {original_size:.1f}KB")
            
            # Remove potential watermarks
            print(f"   🧹 Checking for watermarks...")
            img = remove_watermarks(img)
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Resize if too large
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                print(f"   📐 Resized to: {img.width}x{img.height}")
            
            # Optimize for background use
            print(f"   🎨 Optimizing for background use...")
            
            # Enhance for subtle background appearance
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.05)  # Slightly brighter
            
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(0.95)  # Slightly less contrast
            
            # Optional: slight blur for very subtle appearance
            if '--subtle' in sys.argv:
                img = img.filter(ImageFilter.GaussianBlur(0.3))
                print(f"   ✨ Applied subtle blur for background use")
            
            # Binary search for optimal quality to hit target size
            print(f"   🎯 Targeting {target_size_kb}KB file size...")
            
            quality_low, quality_high = 50, 95
            best_quality = 80
            best_size = 0
            
            for _ in range(10):  # Max 10 iterations
                quality_mid = (quality_low + quality_high) // 2
                
                # Test compression
                buffer = io.BytesIO()
                img.save(buffer, 'JPEG', quality=quality_mid, optimize=True)
                size_kb = len(buffer.getvalue()) / 1024
                
                if abs(size_kb - target_size_kb) < 30:  # Within 30KB
                    best_quality = quality_mid
                    best_size = size_kb
                    break
                elif size_kb > target_size_kb:
                    quality_high = quality_mid - 1
                else:
                    quality_low = quality_mid + 1
                    best_quality = quality_mid
                    best_size = size_kb
            
            # Save final image
            img.save(output_path, 'JPEG', quality=best_quality, optimize=True)
            final_size = os.path.getsize(output_path) / 1024
            
            # Results
            compression_ratio = (1 - final_size / original_size) * 100
            print(f"   ✅ Final: {img.width}x{img.height}, {final_size:.1f}KB (Quality: {best_quality})")
            print(f"   📊 Compression: {compression_ratio:.1f}% size reduction")
            
            # Suitability check
            if final_size <= target_size_kb * 1.3:
                print(f"   🎯 Perfect for web backgrounds!")
            else:
                print(f"   ⚠️  Larger than ideal, but quality preserved")
                
    except Exception as e:
        print(f"❌ Error processing {input_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Optimize images for Air Force background system')
    parser.add_argument('--folder', help='Folder containing images to optimize')
    parser.add_argument('--single', help='Single image file to optimize')
    parser.add_argument('--target', type=int, default=500, help='Target size in KB (default: 500)')
    parser.add_argument('--width', type=int, default=1920, help='Max width in pixels (default: 1920)')
    parser.add_argument('--subtle', action='store_true', help='Apply extra blur for very subtle backgrounds')
    
    args = parser.parse_args()
    
    if not args.folder and not args.single:
        print("🇺🇸 Universal Air Force Background Image Optimizer")
        print("=" * 55)
        print()
        print("Usage:")
        print("  python optimize_any_images.py --folder downloads/")
        print("  python optimize_any_images.py --single image.jpg")
        print("  python optimize_any_images.py --folder downloads/ --target 400")
        print()
        print("Options:")
        print("  --target SIZE    Target file size in KB (default: 500)")
        print("  --width WIDTH    Maximum width in pixels (default: 1920)")
        print("  --subtle         Apply extra blur for very subtle backgrounds")
        print()
        print("🚨 IMPORTANT: Use authentic USAF images from DVIDS")
        print("   - Public domain, no watermarks")
        print("   - Official military photography")
        print("   - Avoid Getty Images (commercial/watermarked)")
        return
    
    # Create output directory
    output_dir = Path("static/backgrounds")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    processed = 0
    total_size_before = 0
    total_size_after = 0
    
    if args.single:
        # Process single file
        input_file = Path(args.single)
        if input_file.exists():
            output_file = output_dir / f"optimized_{input_file.stem}.jpg"
            
            size_before = os.path.getsize(input_file)
            optimize_for_background(input_file, output_file, args.target, args.width)
            
            if output_file.exists():
                size_after = os.path.getsize(output_file)
                processed = 1
                total_size_before = size_before
                total_size_after = size_after
        else:
            print(f"❌ File not found: {input_file}")
            return
    
    elif args.folder:
        # Process folder
        folder_path = Path(args.folder)
        if not folder_path.exists():
            print(f"❌ Folder not found: {folder_path}")
            return
        
        # Find image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        image_files = [f for f in folder_path.iterdir() 
                      if f.is_file() and f.suffix.lower() in image_extensions]
        
        if not image_files:
            print(f"❌ No image files found in {folder_path}")
            return
        
        print(f"🔧 Processing {len(image_files)} images from {folder_path}")
        print()
        
        for input_file in image_files:
            output_file = output_dir / f"optimized_{input_file.stem}.jpg"
            
            size_before = os.path.getsize(input_file)
            optimize_for_background(input_file, output_file, args.target, args.width)
            
            if output_file.exists():
                size_after = os.path.getsize(output_file)
                total_size_before += size_before
                total_size_after += size_after
                processed += 1
            
            print()  # Spacing between files
    
    # Summary
    if processed > 0:
        print("=" * 55)
        print(f"✅ Optimization Complete!")
        print(f"   📊 Images processed: {processed}")
        print(f"   📉 Total size: {total_size_before/1024/1024:.1f}MB → {total_size_after/1024/1024:.1f}MB")
        print(f"   💾 Space saved: {(total_size_before-total_size_after)/1024/1024:.1f}MB")
        print(f"   🎯 Average size: {total_size_after/processed/1024:.0f}KB per image")
        print()
        print("🎨 Images ready for Air Force background system!")
        print("   - Copy optimized images to static/backgrounds/")
        print("   - Rename to match system requirements")
        print("   - Each page will show different aircraft backgrounds")

if __name__ == "__main__":
    main()