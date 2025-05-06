#!/bin/bash

# Execute the Python script
python3 - << 'EOF'
import os
import glob

# Define paths
base_dir = '/Users/allwefantasy/projects/auto-coder'
rules_dir = os.path.join(base_dir, '.autocoderrules')
output_file = os.path.join(base_dir, '.windsurfrules')

print(f"Base directory: {base_dir}")

def read_file(file_path):
    """Read content from a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path, content):
    """Write content to a file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    """Main function to process markdown files and combine them."""
    print(f"Processing rules from {rules_dir}")
    
    # Check if the rules directory exists
    if not os.path.exists(rules_dir):
        print(f"Error: Rules directory {rules_dir} does not exist.")
        return
    
    combined_content = []
    
    # First, try to get the index.md file (case insensitive)
    index_files = glob.glob(os.path.join(rules_dir, '[iI]ndex.md'))
    if index_files:
        index_file = index_files[0]
        print(f"Adding index file: {os.path.basename(index_file)}")
        combined_content.append(read_file(index_file))
    else:
        print("Warning: No index.md file found.")
    
    # Then get all other .md files (excluding index.md)
    md_files = [f for f in glob.glob(os.path.join(rules_dir, '*.md')) 
                if os.path.basename(f).lower() != 'index.md']
    
    # Sort files alphabetically
    md_files.sort()
    
    # Process each markdown file
    for md_file in md_files:
        file_name = os.path.basename(md_file)
        print(f"Adding file: {file_name}")
        content = read_file(md_file)
        combined_content.append(content)
    
    # Combine all content with separator
    final_content = "\n===\n".join(combined_content)
    
    # Write to output file
    write_file(output_file, final_content)
    print(f"Successfully wrote combined rules to {output_file}")

if __name__ == "__main__":
    main()
EOF

# Check if the script executed successfully
if [ $? -eq 0 ]; then
    echo "Rules conversion completed successfully."
else
    echo "Error: Rules conversion failed."
    exit 1
fi
