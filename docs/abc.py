import os

def combine_markdown_files(output_filename="all_combined.md"):
    """
    Combines all .md files in the current directory into a single file.
    
    Args:
        output_filename (str): The name of the output file.
    """
    with open(output_filename, "w") as outfile:
        # Loop through all files in the current directory
        for filename in sorted(os.listdir(".")):
            # Check if the file is a markdown file
            if filename.endswith(".md"):
                # Exclude the output file itself to avoid errors
                if filename == output_filename:
                    continue

                # Write a heading for each file
                outfile.write(f"# Content from {filename}\n\n")
                
                # Write the content of the file
                with open(filename, "r") as infile:
                    outfile.write(infile.read())
                
                # Add a separator for readability
                outfile.write("\n\n---\n\n")

    print(f"All Markdown files have been combined into {output_filename}")

# Run the function
combine_markdown_files()