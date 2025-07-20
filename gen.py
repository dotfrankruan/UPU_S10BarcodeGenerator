#!/usr/bin/env python3
# UPU S10 Barcode Generator
#
# This script generates UPU S10 standard barcode images (Code128) with
# an enhanced visual style, including larger text and a bottom color bar,
# inspired by real-world postal labels.
#
# Author: Gemini
#
# Required libraries:
# - python-barcode: For generating the barcode itself.
# - Pillow: For creating the final image with custom text and styling.
#
# You can install them using pip:
# pip install python-barcode Pillow
#

import argparse
import os
import sys
from barcode import get_barcode_class
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont

def calculate_s10_checksum(serial_number: str) -> int:
    """
    Calculates the checksum digit for an 8-digit UPU S10 serial number.

    The algorithm uses a weighted sum of the digits.
    Weights: [8, 6, 4, 2, 3, 5, 9, 7]

    Args:
        serial_number: An 8-digit string.

    Returns:
        The single-digit checksum.
    """
    if not serial_number.isdigit() or len(serial_number) != 8:
        raise ValueError("Serial number must be an 8-digit string.")

    weights = [8, 6, 4, 2, 3, 5, 9, 7]
    
    s = sum(int(digit) * weight for digit, weight in zip(serial_number, weights))
    checksum = 11 - (s % 11)

    if checksum == 10:
        return 0
    elif checksum == 11:
        return 5
    else:
        return checksum

def format_s10_text(s10_id: str) -> str:
    """
    Formats the 13-character S10 ID into the standard UPU display format.
    Example: HF600000007CN -> HF 6000 0000 7 CN

    Args:
        s10_id: The full 13-character S10 identifier.

    Returns:
        A formatted string with spaces.
    """
    si = s10_id[0:2]
    sn1 = s10_id[2:6]
    sn2 = s10_id[6:10]
    cs = s10_id[10:11]
    cc = s10_id[11:13]
    return f"{si} {sn1} {sn2} {cs} {cc}"

def generate_upu_barcode(s10_id: str, output_filename: str, code_extension: str):
    """
    Generates and saves a UPU S10 barcode image with an enhanced visual style.

    This function creates a Code128 barcode, then uses Pillow to draw it
    onto a new canvas with enlarged, formatted text. A green bar is added
    at the bottom only for numeric (provincial) codes.

    Args:
        s10_id: The full 13-character S10 identifier.
        output_filename: The path to save the final PNG image.
        code_extension: The 2-character code, used to determine if a green bar is needed.
    """
    try:
        # --- 1. Generate Barcode (without text) ---
        code128 = get_barcode_class('code128')
        writer_options = {
            "write_text": False,
            "module_height": 15.0,
            "module_width": 0.4, # Slightly wider bars
            "quiet_zone": 2.0,
        }
        barcode_image = code128(s10_id, writer=ImageWriter()).render(writer_options)

        # --- 2. Define Visual Style ---
        FONT_SIZE = 48
        TEXT_AREA_HEIGHT = 80  # Fixed height for the text area below the barcode
        GREEN_BAR_HEIGHT = 30
        GREEN_COLOR = '#1E8449' # A shade of postal green
        is_provincial = code_extension.isdigit()

        # --- 3. Prepare Canvas and Font ---
        formatted_text = format_s10_text(s10_id)
        try:
            # Use a clear, bold font like Arial Black if available
            font = ImageFont.truetype("ariblk.ttf", FONT_SIZE)
        except IOError:
            print("Warning: Arial Black font not found. Using default bold font.")
            try:
                # Fallback to Courier Bold
                font = ImageFont.truetype("courbd.ttf", FONT_SIZE)
            except IOError:
                font = ImageFont.load_default()

        # Get text dimensions to calculate canvas size and position
        text_bbox = font.getbbox(formatted_text)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        barcode_width, barcode_height = barcode_image.size
        
        # Calculate final image height based on fixed areas
        final_height = barcode_height + TEXT_AREA_HEIGHT
        if is_provincial:
            final_height += GREEN_BAR_HEIGHT
        
        # Create a new blank image with a white background
        final_image = Image.new('RGB', (barcode_width, final_height), 'white')
        draw = ImageDraw.Draw(final_image)

        # --- 4. Composite the Image ---
        # Paste the barcode at the top
        final_image.paste(barcode_image, (0, 0))

        # Calculate text position to center it horizontally and vertically in its area
        text_x = (barcode_width - text_width) / 2
        text_area_y_start = barcode_height
        text_y = text_area_y_start + (TEXT_AREA_HEIGHT - text_height) / 2
        
        # Draw the enlarged text
        draw.text((text_x, text_y), formatted_text, fill='black', font=font)
        
        # Draw the green bar at the very bottom ONLY for provincial codes
        if is_provincial:
            bar_y_start = final_height - GREEN_BAR_HEIGHT
            draw.rectangle([(0, bar_y_start), (barcode_width, final_height)], fill=GREEN_COLOR)

        # --- 5. Save the Final Image ---
        final_image.save(output_filename)

    except Exception as e:
        raise Exception(f"An error occurred during barcode generation for {s10_id}: {e}")


def main():
    """Main function to parse arguments and run the generator."""
    parser = argparse.ArgumentParser(
        description="Generate UPU S10 barcode images in a batch with enhanced styling.",
        epilog="Examples:\n"
               "  Standard: python upu_generator.py HF 60000000 CN 25 -d ./barcodes\n"
               "  Regional: python upu_generator.py KA 12345678 11 50 -d ./provincial_barcodes",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "service_indicator",
        type=str,
        help="The 2-character service indicator (e.g., 'HF', 'RA')."
    )
    parser.add_argument(
        "start_serial_number",
        type=str,
        help="The starting 8-digit serial number (e.g., '60000000')."
    )
    parser.add_argument(
        "country_or_regional_code",
        type=str,
        help="The 2-character destination country code or regional extension (e.g., 'CN', '11')."
    )
    parser.add_argument(
        "quantity",
        type=int,
        help="The number of barcodes to generate."
    )
    parser.add_argument(
        "-d", "--directory",
        type=str,
        default="barcodes",
        help="Output directory for the PNG images. Defaults to './barcodes'."
    )

    args = parser.parse_args()

    # --- Input Validation ---
    if len(args.service_indicator) != 2 or not args.service_indicator.isalpha():
        print("Error: Service indicator must be 2 alphabetic characters.", file=sys.stderr)
        sys.exit(1)
    
    if len(args.start_serial_number) != 8 or not args.start_serial_number.isdigit():
        print("Error: Starting serial number must be 8 digits.", file=sys.stderr)
        sys.exit(1)

    if len(args.country_or_regional_code) != 2 or not args.country_or_regional_code.isalnum():
        print("Error: Country/regional code must be 2 alphanumeric characters.", file=sys.stderr)
        sys.exit(1)
        
    if args.quantity <= 0:
        print("Error: Quantity must be a positive integer.", file=sys.stderr)
        sys.exit(1)

    # --- Prepare for Batch Generation ---
    si = args.service_indicator.upper()
    cc = args.country_or_regional_code.upper()
    start_sn = int(args.start_serial_number)
    
    output_dir = args.directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Generating {args.quantity} barcodes into directory '{output_dir}'...")

    # --- Generation Loop ---
    for i in range(args.quantity):
        current_sn_int = start_sn + i
        sn_str = str(current_sn_int).zfill(8)
        
        if len(sn_str) > 8:
            print(f"\nWarning: Serial number has exceeded 8 digits ('99999999'). Stopping at {i} barcodes.", file=sys.stderr)
            break
            
        try:
            cs = calculate_s10_checksum(sn_str)
            full_s10_id = f"{si}{sn_str}{cs}{cc}"
            output_filename = os.path.join(output_dir, f"{full_s10_id}.png")
            generate_upu_barcode(full_s10_id, output_filename, cc)
            
            sys.stdout.write(f"\r✅ Generated {i+1}/{args.quantity}: {full_s10_id}")
            sys.stdout.flush()

        except Exception as e:
            print(f"\n❌ Error: {e}", file=sys.stderr)
            sys.exit(1)
            
    print("\nBatch generation complete.")


if __name__ == "__main__":
    main()

