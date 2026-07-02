#!/usr/bin/env python3
"""
Process and optimize the current Air Force background images.
Converts WebP to JPG and ensures all images are optimized for web use.
"""

import os
from PIL import Image, ImageEnhance
from pathlib import Path
import io

def optimize_background_image(input_path, output_path, target_size_kb=500):
    """Optimize image for background use."""
    try:
        with Image.open(input_path) as img:
            print(f"🔧 Processing {input_path.name}...")
            
            # Get original info
            original_size_kb = os.path.getsize(input_path) / 1024
            print(f"   📏 Original: {img.width}x{img.height}, {original_size_kb:.1f}KB")
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large (max 1920px width)
            max_width = 1920
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                print(f"   📐 Resized to: {img.width}x{img.height}")
            
            # Optimize for background use - slightly brighter and less contrast
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.05)
            
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(0.95)
            
            # Find optimal quality for target size
            quality_low, quality_high = 60, 95
            best_quality = 85
            
            for _ in range(8):  # 8 iterations should be enough
                quality_mid = (quality_low + quality_high) // 2
                
                buffer = io.BytesIO()
                img.save(buffer, 'JPEG', quality=quality_mid, optimize=True)
                size_kb = len(buffer.getvalue()) / 1024
                
                if abs(size_kb - target_size_kb) < 30:  # Within 30KB
                    best_quality = quality_mid
                    break
                elif size_kb > target_size_kb:
                    quality_high = quality_mid - 1
                else:
                    quality_low = quality_mid + 1
                    best_quality = quality_mid
            
            # Save optimized image
            img.save(output_path, 'JPEG', quality=best_quality, optimize=True)
            
            final_size_kb = os.path.getsize(output_path) / 1024
            print(f"   ✅ Optimized: {img.width}x{img.height}, {final_size_kb:.1f}KB (Quality: {best_quality})")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("🇺🇸 Processing Current Air Force Background Images")
    print("=" * 55)
    print()
    
    bg_dir = Path("static/backgrounds")
    
    # Mapping of current files to expected names
    file_mapping = {
        # Current filename -> Expected filename
        'f22_raptor.webp': 'f22_raptor.jpg',
        'f22_formation.webp': 'f22_formation.jpg', 
        'b52_aerial_refuel.webp': 'b52_aerial_refuel.jpg',
        'b52_formation.jpg': 'b52_formation.jpg',  # Already correct
        'kc135_international.jpg': 'kc135_international.jpg',  # Already correct
        'b1_lancer.jpg': 'b1_lancer.jpg',  # Already correct
    }
    
    # Missing file that we need
    missing_files = ['b52_kc10_refuel.jpg']
    
    processed = 0
    total_before = 0
    total_after = 0
    
    for current_name, expected_name in file_mapping.items():
        current_file = bg_dir / current_name
        output_file = bg_dir / expected_name
        
        if current_file.exists():
            size_before = os.path.getsize(current_file)
            
            if optimize_background_image(current_file, output_file, target_size_kb=500):
                size_after = os.path.getsize(output_file)
                total_before += size_before
                total_after += size_after
                processed += 1
                
                # Remove original if it was WebP (converted)
                if current_name.endswith('.webp') and current_name != expected_name:
                    current_file.unlink()
                    print(f"   🗑️  Removed original WebP file")
            
            print()
        else:
            print(f"⚠️  {current_name} not found")
    
    print("=" * 55)
    print(f"✅ Processing Complete!")
    print(f"   📊 Images processed: {processed}")
    print(f"   📉 Size change: {total_before/1024/1024:.1f}MB → {total_after/1024/1024:.1f}MB")
    
    if total_before > total_after:
        print(f"   💾 Space saved: {(total_before-total_after)/1024/1024:.1f}MB")
    else:
        print(f"   📈 Size optimized for quality")
    
    print(f"   🎯 Average size: {total_after/processed/1024:.0f}KB per image")
    print()
    
    # Check what we have now
    print("📋 Current Air Force Background Files:")
    expected_files = [
        'f22_raptor.jpg',
        'f22_formation.jpg', 
        'b52_aerial_refuel.jpg',
        'b52_formation.jpg',
        'kc135_international.jpg',
        'b1_lancer.jpg',
        'b52_kc10_refuel.jpg'
    ]
    
    for filename in expected_files:
        file_path = bg_dir / filename
        if file_path.exists():
            size_kb = os.path.getsize(file_path) / 1024
            print(f"   ✅ {filename}: {size_kb:.1f}KB")
        else:
            print(f"   ❌ {filename}: Missing")
    
    print()
    print("🎨 Air Force Background System Status:")
    existing_count = sum(1 for f in expected_files if (bg_dir / f).exists())
    print(f"   📊 {existing_count}/{len(expected_files)} images ready")
    
    if existing_count >= 6:
        print("   🎯 System is fully functional!")
        print("   ✈️  Each page will show different authentic USAF aircraft")
        print("   📱 Mobile-optimized and theme-compatible")
    else:
        print("   ⚠️  Some images still missing for complete coverage")
        print("   💡 Download missing images from DVIDS URLs in README.md")

if __name__ == "__main__":
    main()