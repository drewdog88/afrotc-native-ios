#!/usr/bin/env python3
"""
US Air Force Background Image Setup Script

This script helps download and optimize authentic US Air Force public domain images
from DVIDS for use as subtle page backgrounds in the AFROTC 695 recruitment system.

All images are public domain works of the United States Air Force.
"""

import os
import sys
from PIL import Image, ImageFilter, ImageEnhance
import requests
from pathlib import Path
import io

# Image configuration
IMAGES = {
    'f22_raptor.jpg': {
        'url': 'https://www.dvidshub.net/image/8582415/us-f-22s-land-basa-air-base-philippines-during-dfe-operations',
        'virin': '240808-F-TK526-1147',
        'description': 'F-22 Raptor - Used for Recruits page',
        'direct_download': None  # DVIDS requires login for downloads
    },
    'f22_formation.jpg': {
        'url': 'https://www.dvidshub.net/image/8585844/us-f-22s-land-mactan-benito-ebuen-air-base-philippines-during-dfe-operations',
        'virin': '240809-F-TK526-1242',
        'description': 'F-22 Formation - Used for Cadets and Login pages',
        'direct_download': None
    },
    'b52_aerial_refuel.jpg': {
        'url': 'https://www.dvidshub.net/image/8219744/aerial-refueling-b-52',
        'virin': '240130-F-WT071-1013',
        'description': 'B-52 Aerial Refueling - Used for Contacts page',
        'direct_download': None
    },
    'b52_formation.jpg': {
        'url': 'https://www.dvidshub.net/image/8904378/b-52h-stratofortress-joins-formation-during-btf-25-2',
        'virin': '250306-F-AE827-1059',
        'description': 'B-52 Formation - Used for Calendar page',
        'direct_download': None
    },
    'kc135_international.jpg': {
        'url': 'https://www.dvidshub.net/image/3816877/international-aerial-refuel',
        'virin': '170925-F-QF982-0255',
        'description': 'KC-135 International Refueling - Used for Materials page',
        'direct_download': None
    },
    'b1_lancer.jpg': {
        'url': 'https://www.dvidshub.net/image/8646233/37th-bomb-squadron-exercise-takeoff',
        'virin': '240916-F-DW056-3826',
        'description': 'B-1B Lancer - Used for Admin page',
        'direct_download': None
    },
    'b52_kc10_refuel.jpg': {
        'url': 'https://www.dvidshub.net/image/2948867/kc-10-extender-maintains-decisive-air-power',
        'virin': '161026-F-CO490-015',
        'description': 'B-52 with KC-10 - Used for System Statistics page',
        'direct_download': None
    }
}

def optimize_image(input_path, output_path, target_size_kb=500, max_width=1920):
    """
    Optimize an image for web use as a background, targeting specific file size.
    
    Args:
        input_path: Path to the input image
        output_path: Path to save the optimized image
        target_size_kb: Target file size in KB
        max_width: Maximum width in pixels
    """
    try:
        with Image.open(input_path) as img:
            print(f"🔧 Processing {input_path.name}...")
            print(f"   Original: {img.width}x{img.height}, {os.path.getsize(input_path)/1024:.1f}KB")
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Calculate new dimensions
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                print(f"   Resized to: {img.width}x{img.height}")
            
            # Enhance image for background use
            # Slight brightness and contrast adjustment for subtle backgrounds
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.1)  # Slightly brighter
            
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(0.9)  # Slightly less contrast for subtlety
            
            # Binary search for optimal quality to hit target file size
            quality_low, quality_high = 60, 95
            best_quality = 85
            
            while quality_low <= quality_high:
                quality_mid = (quality_low + quality_high) // 2
                
                # Test save to memory
                buffer = io.BytesIO()
                img.save(buffer, 'JPEG', quality=quality_mid, optimize=True)
                size_kb = len(buffer.getvalue()) / 1024
                
                if abs(size_kb - target_size_kb) < 50:  # Within 50KB of target
                    best_quality = quality_mid
                    break
                elif size_kb > target_size_kb:
                    quality_high = quality_mid - 1
                else:
                    quality_low = quality_mid + 1
                    best_quality = quality_mid
            
            # Save final optimized image
            img.save(output_path, 'JPEG', quality=best_quality, optimize=True)
            
            # Get final file size
            final_size_kb = os.path.getsize(output_path) / 1024
            print(f"   ✓ Optimized: {img.width}x{img.height}, {final_size_kb:.1f}KB (Quality: {best_quality})")
            
            # Verify it's suitable for background use
            if final_size_kb <= target_size_kb * 1.2:  # Within 20% of target
                print(f"   ✅ Perfect for web backgrounds!")
            else:
                print(f"   ⚠️  Larger than target, but optimized for quality")
            
    except Exception as e:
        print(f"✗ Error optimizing {input_path}: {e}")

def remove_potential_watermarks(img):
    """
    Remove potential watermarks or overlays from images.
    Note: DVIDS images shouldn't have watermarks, but this provides cleanup if needed.
    """
    # This is a placeholder function - DVIDS images are clean public domain
    # If watermarks are found, this could be enhanced with specific removal techniques
    return img

def download_image_from_url(url, output_path):
    """
    Attempt to download image directly from URL (if available).
    Note: DVIDS typically requires login for high-res downloads.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
    except:
        pass
    return False

def main():
    """Main function to set up USAF background images."""
    print("🇺🇸 US Air Force Background Image Setup")
    print("=" * 50)
    print()
    
    # Create backgrounds directory
    bg_dir = Path("static/backgrounds")
    bg_dir.mkdir(parents=True, exist_ok=True)
    
    print("📋 Required Images:")
    print()
    
    for filename, info in IMAGES.items():
        print(f"📸 {filename}")
        print(f"   Description: {info['description']}")
        print(f"   DVIDS URL: {info['url']}")
        print(f"   VIRIN: {info['virin']}")
        print()
    
    print("📥 Download Instructions:")
    print("1. Visit each DVIDS URL above")
    print("2. Click 'Register/Login to Download' (free DVIDS account required)")
    print("3. Download the highest resolution version available")
    print("4. Place the downloaded images in the 'downloads' folder")
    print("5. Run this script with --optimize to process them")
    print()
    
    print("🚨 IMPORTANT: Getty Images vs DVIDS")
    print("   - These are AUTHENTIC US Air Force images from DVIDS")
    print("   - They are PUBLIC DOMAIN with NO watermarks")
    print("   - Do NOT use Getty Images (commercial, watermarked)")
    print("   - DVIDS images are free and official military photography")
    print()
    
    # Check for flags
    if '--optimize' in sys.argv:
        downloads_dir = Path("downloads")
        if not downloads_dir.exists():
            print("❌ Downloads folder not found. Please create 'downloads' folder and add images.")
            return
        
        print("🔧 Optimizing images for web use (~500KB each)...")
        print()
        
        optimized_count = 0
        total_size_before = 0
        total_size_after = 0
        
        for filename in IMAGES.keys():
            input_file = downloads_dir / filename
            output_file = bg_dir / filename
            
            if input_file.exists():
                size_before = os.path.getsize(input_file)
                total_size_before += size_before
                
                optimize_image(input_file, output_file, target_size_kb=500)
                
                if output_file.exists():
                    size_after = os.path.getsize(output_file)
                    total_size_after += size_after
                    optimized_count += 1
                
                print()
            else:
                print(f"⚠️  {filename} not found in downloads folder")
        
        print("=" * 50)
        print(f"✅ Optimization Complete!")
        print(f"   📊 Images processed: {optimized_count}")
        print(f"   📉 Size reduction: {(total_size_before/1024/1024):.1f}MB → {(total_size_after/1024/1024):.1f}MB")
        print(f"   💾 Space saved: {((total_size_before-total_size_after)/1024/1024):.1f}MB")
        print(f"   🎯 Average size: {(total_size_after/optimized_count/1024):.0f}KB per image")
        
        if optimized_count > 0:
            print()
            print("🎨 Air Force Background System is now ACTIVE!")
            print("   ✈️  Each page shows different authentic USAF aircraft")
            print("   🔍 Backgrounds are subtle and maintain readability") 
            print("   🎨 Works with both Original and Air Force themes")
            print("   📱 Mobile-optimized with reduced opacity")
            print("   🖨️  Print-friendly (backgrounds hidden when printing)")
    
    elif '--check' in sys.argv:
        print("🔍 Checking current background images...")
        print()
        
        for filename in IMAGES.keys():
            bg_file = bg_dir / filename
            if bg_file.exists():
                size_kb = os.path.getsize(bg_file) / 1024
                with Image.open(bg_file) as img:
                    print(f"✅ {filename}: {img.width}x{img.height}, {size_kb:.1f}KB")
            else:
                print(f"❌ {filename}: Not found")
    
    else:
        print("💡 Available commands:")
        print("   python download_usaf_images.py --optimize   # Optimize downloaded images")
        print("   python download_usaf_images.py --check      # Check current images")
        print()
        print("🎯 Target: ~500KB per image for optimal web performance")

if __name__ == "__main__":
    main()