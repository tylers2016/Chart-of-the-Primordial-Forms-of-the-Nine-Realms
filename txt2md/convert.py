import re

def generate_chinese_numerals_for_h2():
    """Generates a list of Chinese numerals from 1 to 38 for H2 regex."""
    numerals = []
    units = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
    
    # 1-9
    for i in range(1, 10):
        numerals.append(units[i])
    # 10
    numerals.append("十")
    # 11-19
    for i in range(1, 10):
        numerals.append("十" + units[i])
    # 20
    numerals.append("二十")
    # 21-29
    for i in range(1, 10):
        numerals.append("二十" + units[i])
    # 30
    numerals.append("三十")
    # 31-38
    for i in range(1, 9): # up to 38
        numerals.append("三十" + units[i])
    
    # Order for regex: longer first to ensure correct matching (e.g., "十一" before "一")
    # This is generally good practice, though Python's re might handle it.
    # For this specific list, the generated order is mostly fine, but explicit sort by length desc is safer.
    numerals.sort(key=len, reverse=True)
    return numerals

# Pre-compile regex patterns
H1_PATTERN = re.compile(r"^第[0-9]+章\s*.*$")

# Generate H2 pattern from Chinese numerals
CHINESE_NUMERALS_H2_LIST = generate_chinese_numerals_for_h2()
H2_REGEX_PART = "(?:" + "|".join(CHINESE_NUMERALS_H2_LIST) + ")"
H2_PATTERN = re.compile(r"^" + H2_REGEX_PART + r"、\s*.*$")

# H3 pattern for actual content (numbers 1-25)
# Group 1: Number, Group 2: Place name with optional suffix
H3_CONTENT_PATTERN = re.compile(
    r"([1-9]|1[0-9]|2[0-5])\.([\u4e00-\u9fa5]{2,15}?(?:区|市|县|自治县|旗|自治旗|特区|林区)?)"
)

def process_text_to_markdown(input_filepath, output_filepath):
    """
    Processes a text file according to specified rules and converts it to Markdown.
    """
    log_messages = []
    h1_just_processed = False
    h2_just_processed = False
    current_h1_context = None
    current_h2_context = None
    expected_h3_number = 1
    
    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile, \
             open(output_filepath, 'w', encoding='utf-8') as outfile:
            
            for line_num, original_line in enumerate(infile, 1):
                line = original_line.strip() # Work with stripped line for matching, but write original if needed or reconstructed
                                             # For this project, we reconstruct/write stripped parts mostly.

                # Skip processing for genuinely empty lines after stripping
                if not line:
                    outfile.write("\n") # Preserve empty line from source if it was just a newline
                    continue

                # --- Level 1: H1 ---
                if H1_PATTERN.match(line):
                    outfile.write(f"# {line}\n")
                    current_h1_context = line
                    current_h2_context = None # Reset H2 context
                    expected_h3_number = 1    # Reset H3 expectation
                    h1_just_processed = True
                    h2_just_processed = False # Clear H2 flag
                    continue 

                # --- Insertion: "## 零、上位类说明" (H2 after H1) ---
                if h1_just_processed:
                    outfile.write("## 零、上位类说明\n")
                    h1_just_processed = False
                    # Current line still needs processing

                # --- Level 2: H2 ---
                if H2_PATTERN.match(line):
                    outfile.write(f"## {line}\n")
                    current_h2_context = line
                    expected_h3_number = 1    # Reset H3 expectation for this new H2
                    h2_just_processed = True
                    h1_just_processed = False # Clear H1 flag
                    continue

                # --- Insertion: "### 0.上位类说明" (H3 after H2) ---
                if h2_just_processed:
                    outfile.write("### 0.上位类说明\n")
                    h2_just_processed = False
                    # `expected_h3_number` remains 1 for the *actual* first H3
                    # Current line still needs processing
                
                # --- Level 3: H3 (Content) and Plain Text ---
                # This line was not an H1 or H2. Process for H3s or as plain text.
                current_pos_in_line = 0
                line_processed_for_h3 = False # Flag to see if any H3 was found and processed in this line

                # Buffer to build output for the current original line, which might be split
                output_parts_for_current_line = []

                while current_pos_in_line < len(line):
                    match_h3 = H3_CONTENT_PATTERN.search(line, current_pos_in_line)
                    if match_h3:
                        line_processed_for_h3 = True
                        # Text before H3
                        text_before_h3 = line[current_pos_in_line:match_h3.start()].strip()
                        if text_before_h3:
                            output_parts_for_current_line.append(text_before_h3 + "\n")
                        
                        # H3 Content
                        h3_full_text = match_h3.group(0) # e.g., "1.长安区"
                        h3_number_str = match_h3.group(1)
                        h3_name_part = match_h3.group(2) # For potential future use, not directly used now but good to have

                        try:
                            h3_number_int = int(h3_number_str)
                            
                            # H3 Number Validation
                            if current_h2_context: # Primary validation context
                                if h3_number_int != expected_h3_number:
                                    log_messages.append(
                                        f"L{line_num}: H3 numbering mismatch under H2 '{current_h2_context}'. "
                                        f"Expected '{expected_h3_number}.', found '{h3_number_int}. ({h3_name_part})'. "
                                        f"H1: '{current_h1_context}'."
                                    )
                            elif current_h1_context : # H3 appears under H1 but not under a specific H2 (e.g. after "零、上位类说明")
                                 if h3_number_int != expected_h3_number: # Should expect 1 if reset by H1
                                    log_messages.append(
                                        f"L{line_num}: H3 numbering mismatch under H1 '{current_h1_context}' (no active H2). "
                                        f"Expected '{expected_h3_number}.', found '{h3_number_int}. ({h3_name_part})'."
                                    )
                            else: # No H1 or H2 context, highly unlikely if structure is followed
                                log_messages.append(
                                     f"L{line_num}: H3 '{h3_full_text}' found without H1/H2 context. Number: {h3_number_int}."
                                )
                            
                            expected_h3_number = h3_number_int + 1
                        except ValueError:
                             log_messages.append(f"L{line_num}: Could not parse H3 number: {h3_number_str} in '{h3_full_text}'")


                        output_parts_for_current_line.append(f"### {h3_full_text}\n")
                        current_pos_in_line = match_h3.end()
                    else:
                        # No more H3s in the remainder of the line
                        remaining_text = line[current_pos_in_line:].strip()
                        if remaining_text:
                            output_parts_for_current_line.append(remaining_text + "\n")
                        break # Exit while loop for this line
                
                if output_parts_for_current_line:
                    for part in output_parts_for_current_line:
                        outfile.write(part)
                elif not line_processed_for_h3 and line: # It was a non-empty line, not H1/H2, and had no H3s. Plain text.
                    outfile.write(line + "\n")

    except FileNotFoundError:
        log_messages.append(f"Error: Input file '{input_filepath}' not found.")
    except Exception as e:
        log_messages.append(f"An unexpected error occurred: {e}")

    # Print log messages
    if log_messages:
        print("Processing Log:")
        for msg in log_messages:
            print(msg)
    else:
        print(f"Processing complete. Output written to '{output_filepath}'. No issues logged.")

if __name__ == '__main__':
    # You should replace 'input.txt' with the actual path to your input file
    # For example, if '新建 文本文档.txt' is in the same directory as the script:
    input_file = '新建 文本文档.txt' 
    # If it's in a different location, provide the full or relative path.
    # e.g., input_file = 'path/to/your/新建 文本文档.txt' 
    
    output_file = 'output.md'
    
    # Check if the default input file exists, otherwise prompt user or use a placeholder
    import os
    if not os.path.exists(input_file):
        print(f"Warning: Default input file '{input_file}' not found.")
        # Example of asking the user:
        # input_file_from_user = input(f"Please enter the path to your TXT file (or press Enter to skip processing): ")
        # if not input_file_from_user:
        #     print("No input file provided. Exiting.")
        #     exit()
        # input_file = input_file_from_user
        print("Please ensure '新建 文本文档.txt' is in the same directory as the script,")
        print("or modify the 'input_file' variable in the script with the correct path.")
    else:
        process_text_to_markdown(input_file, output_file)