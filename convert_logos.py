import os
import sys

LOGO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos")

print("NHL Logo Converter - SVG to PNG")
print("="*60)

# Check for required libraries
try:
    from PIL import Image
    import io
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

# Try to import svg rendering library
converter_available = None

# Try cairosvg
try:
    import cairosvg
    converter_available = 'cairosvg'
    print("Using cairosvg for conversion...")
except (ImportError, OSError):
    # OSError occurs when cairosvg is installed but Cairo DLLs are missing
    pass

# Try svglib
if not converter_available:
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        converter_available = 'svglib'
        print("Using svglib for conversion...")
    except (ImportError, OSError):
        # OSError occurs when svglib is installed but Cairo DLLs are missing
        pass

# Try selenium with Chrome (last resort)
if not converter_available:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        converter_available = 'selenium'
        print("Using Selenium with Chrome for conversion...")
    except ImportError:
        pass

if not converter_available:
    print("\nNo SVG converter available!")
    print("\nInstall one of these options:")
    print("  1. pip install cairosvg (requires Cairo DLLs)")
    print("  2. pip install svglib reportlab (requires Cairo DLLs)")
    print("  3. pip install selenium (requires Chrome browser)")
    print("\nOr use online converter: https://www.freeconvert.com/svg-to-png")
    input("\nPress Enter to exit...")
    sys.exit(1)

print()

svg_files = [f for f in os.listdir(LOGO_DIR) if f.endswith('.svg')]

if not svg_files:
    print("No SVG files found in logos directory.")
    sys.exit(0)

print(f"Found {len(svg_files)} SVG files to convert.\n")

converted = 0
skipped = 0
failed = 0

for svg_file in svg_files:
    svg_path = os.path.join(LOGO_DIR, svg_file)
    png_file = svg_file.replace('.svg', '.png')
    png_path = os.path.join(LOGO_DIR, png_file)
    
    if os.path.exists(png_path):
        print(f"  ⊘ {png_file} already exists, skipping...")
        skipped += 1
        continue
    
    try:
        if converter_available == 'cairosvg':
            cairosvg.svg2png(url=svg_path, write_to=png_path)
            print(f"  ✓ Converted {svg_file} → {png_file}")
            converted += 1
            
        elif converter_available == 'svglib':
            drawing = svg2rlg(svg_path)
            renderPM.drawToFile(drawing, png_path, fmt="PNG")
            print(f"  ✓ Converted {svg_file} → {png_file}")
            converted += 1
            
        elif converter_available == 'selenium':
            # Use Chrome to render SVG
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            driver = webdriver.Chrome(options=chrome_options)
            
            # Load SVG and take screenshot
            driver.get(f'file:///{svg_path}')
            driver.save_screenshot(png_path)
            driver.quit()
            
            print(f"  ✓ Converted {svg_file} → {png_file}")
            converted += 1
            
    except Exception as e:
        print(f"  ✗ Failed to convert {svg_file}: {e}")
        failed += 1

print("\n" + "="*60)
print(f"Conversion complete!")
print(f"  Converted: {converted}")
print(f"  Skipped: {skipped}")
print(f"  Failed: {failed}")
print("="*60)

if converted > 0:
    print("\n✓ You can now run NHLscores.py to see the logos!")
elif failed > 0:
    print("\n⚠ Some conversions failed. You may need to use an online converter.")
    print("   Visit: https://www.freeconvert.com/svg-to-png")

input("\nPress Enter to exit...")