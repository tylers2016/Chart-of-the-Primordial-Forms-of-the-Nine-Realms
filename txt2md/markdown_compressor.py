#!/usr/bin/env python3
"""
Markdown Compressor

This script processes Markdown files by removing line breaks and spaces from all text
except for headings. Headers (lines starting with '#') remain unchanged.
"""

import sys
import re
import os

def compress_markdown(input_file, output_file=None):
    """
    Compress a markdown file by removing line breaks and spaces from non-header text.
    
    Args:
        input_file (str): Path to the input markdown file
        output_file (str, optional): Path to the output file. If None, will create 
                                    a file with "_compressed" suffix in the same directory.
    
    Returns:
        str: Path to the output file
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return None
    
    # Generate output filename if not provided
    if output_file is None:
        file_name, file_ext = os.path.splitext(input_file)
        output_file = f"{file_name}_compressed{file_ext}"
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split content into blocks based on headers
        blocks = re.split(r'(^#{1,6}\s+.*$)', content, flags=re.MULTILINE)
        
        processed_blocks = []
        for i, block in enumerate(blocks):
            if i % 2 == 1:  # This is a header block (odd index after split)
                processed_blocks.append(block)  # Keep header as is
            else:
                # For non-header blocks, remove line breaks and extra spaces
                # First, preserve code blocks
                code_parts = re.split(r'(```.*?```|`.*?`)', block, flags=re.DOTALL)
                for j, part in enumerate(code_parts):
                    # Skip code blocks (odd indices after split)
                    if j % 2 == 0:
                        # Replace multiple spaces with single space
                        part = re.sub(r'\s+', ' ', part)
                        # Remove spaces at the beginning and end
                        part = part.strip()
                        code_parts[j] = part
                # Join the parts back together
                processed_blocks.append(''.join(code_parts))
        
        # Join all blocks back
        processed_content = '\n'.join(block for block in processed_blocks if block)
        
        # Write to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        print(f"Successfully compressed markdown file to: {output_file}")
        return output_file
    
    except Exception as e:
        print(f"Error processing file: {e}")
        return None

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python markdown_compressor.py input_file.md [output_file.md]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    compress_markdown(input_file, output_file)

if __name__ == "__main__":
    main()