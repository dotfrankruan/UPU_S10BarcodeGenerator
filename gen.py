#!/usr/bin/env python3
# UPU S10 Barcode Generator
#
# This script generates a UPU S10 standard barcode image (Code128) with
# the correctly formatted text underneath.
# The logic for the checksum calculation is based on the provided HTML file.
#
# Required libraries:
# - python-barcode: For generating the barcode itself.
# - Pillow: For creating the final image with custom text.
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
    
    # Calculate the weighted sum
    s = sum(int(digit) * weight for digit, weight in zip(serial_number, weights))
    
    # Calculate the checksum
    checksum = 11 - (s % 11)

    # Apply special UPU rules
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

def generate_upu_barcode(s10_id: str, output_filename: str):
    """
    Generates and saves a UPU S10 barcode image.

    This function creates a Code128 barcode, then uses Pillow to draw it
    onto a new canvas with the specially formatted S10 text underneath.

    Args:
        s10_id: The full 13-character S10 identifier.
        output_filename: The path to save the final PNG image.
    """
    try:
        # --- 1. Generate Barcode (without text) ---
        code128 = get_barcode_class('code128')
        # The writer options suppress the default text under the barcode
        writer_options = {
            "write_text": False,
            "module_height": 15.0, # Standard height
            "module_width": 0.3,   # Controls the width of the bars
            "quiet_zone": 5.0,     # White space on the sides
        }
        barcode_image = code128(s10_id, writer=ImageWriter()).render(writer_options)

        # --- 2. Create the Final Image with Custom Text using Pillow ---
        barcode_width, barcode_height = barcode_image.size
        text_area_height = 40  # Space below the barcode for text
        final_height = barcode_height + text_area_height
        
        # Create a new blank image with a white background
        final_image = Image.new('RGB', (barcode_width, final_height), 'white')
        
        # Paste the generated barcode onto the blank image
        final_image.paste(barcode_image, (0, 0))

        # --- 3. Add the Formatted Text ---
        draw = ImageDraw.Draw(final_image)
        formatted_text = format_s10_text(s10_id)
        
        # Try to load a monospaced font, fallback to default
        try:
            # Use a common monospaced font for better alignment
            font = ImageFont.truetype("cour.ttf", 28) # Courier New
        except IOError:
            print("Warning: Courier font not found. Using default font.")
            font = ImageFont.load_default()

        # Calculate text position to center it
        text_width = draw.textlength(formatted_text, font=font)
        text_x = (barcode_width - text_width) / 2
        text_y = barcode_height + 5 # Position text below the barcode
        
        draw.text((text_x, text_y), formatted_text, fill='black', font=font)

        # --- 4. Save the Final Image ---
        final_image.save(output_filename)
        print(f"✅ Successfully generated barcode and saved to '{output_filename}'")

    except Exception as e:
        print(f"❌ An error occurred during barcode generation: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main function to parse arguments and run the generator."""
    parser = argparse.ArgumentParser(
        description="Generate a UPU S10 barcode image.",
        epilog="Example: python upu_generator.py RD 60000000 CN -o my_barcode.png"
    )
    parser.add_argument(
        "service_indicator",
        type=str,
        help="The 2-character service indicator (e.g., 'HF', 'RA')."
    )
    parser.add_argument(
        "serial_number",
        type=str,
        help="The 8-digit serial number (e.g., '60000000')."
    )
    parser.add_argument(
        "country_code",
        type=str,
        help="The 2-character destination country code / region code (e.g., 'CN', 'US' or '31', '32')."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output filename for the PNG image. Defaults to '<s10_id>.png'."
    )

    args = parser.parse_args()

    # --- Input Validation ---
    if len(args.service_indicator) != 2 or not args.service_indicator.isalpha():
        print("Error: Service indicator must be 2 alphabetic characters.", file=sys.stderr)
        sys.exit(1)
    
    if len(args.serial_number) != 8 or not args.serial_number.isdigit():
        print("Error: Serial number must be 8 digits.", file=sys.stderr)
        sys.exit(1)

#    if len(args.country_code) != 2 or not args.country_code.isalpha():
#        print("Error: Country code must be 2 alphabetic characters.", file=sys.stderr)
#        sys.exit(1)

    # --- Generate S10 ID ---
    si = args.service_indicator.upper()
    sn = args.serial_number
    cc = args.country_code.upper()
    
    try:
        cs = calculate_s10_checksum(sn)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    full_s10_id = f"{si}{sn}{cs}{cc}"
    
    print(f"Generated S10 ID: {full_s10_id}")
    print(f"Formatted Text: {format_s10_text(full_s10_id)}")

    # --- Set Output Filename ---
    if args.output:
        output_filename = args.output
        # Ensure it has a .png extension
        if not output_filename.lower().endswith('.png'):
            output_filename += '.png'
    else:
        output_filename = f"{full_s10_id}.png"

    # --- Generate Barcode ---
    generate_upu_barcode(full_s10_id, output_filename)


if __name__ == "__main__":
    main()

