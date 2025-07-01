#!/bin/bash

# Script to convert HTML files to HAML in subdirectories
# Makes it idempotent - won't recreate HAML files if they already exist and are newer

echo "Converting HTML files to HAML..."

# Find all HTML files in subdirectories (not in root)
find . -mindepth 2 -name "*.html" -type f | while read html_file; do
    # Get the directory and filename without extension
    dir=$(dirname "$html_file")
    basename=$(basename "$html_file" .html)
    haml_file="$dir/$basename.haml"
    
    echo "Processing: $html_file"
    
    # Check if HAML file already exists and is newer than HTML file
    if [ -f "$haml_file" ] && [ "$haml_file" -nt "$html_file" ]; then
        echo "  Skipping - HAML file already exists and is up to date: $haml_file"
        continue
    fi
    
    # Convert HTML to HAML
    if html2haml "$html_file" "$haml_file"; then
        echo "  Successfully created: $haml_file"
    else
        echo "  Error converting: $html_file"
    fi
done

echo "HAML conversion complete!"
