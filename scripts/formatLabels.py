import os

def rename_txt_files(folder_path):
    # Ensure the folder exists
    if not os.path.isdir(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        return

    for filename in os.listdir(folder_path):
        # Work only with .txt files
        if filename.endswith(".txt") and '-' in filename:
            new_name = filename.split('-', 1)[1]  # Keep everything after the first hyphen
            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, new_name)

            # Rename the file
            os.rename(old_path, new_path)
            print(f"Renamed: {filename} -> {new_name}")

if __name__ == "__main__":
    folder = r"C:\Users\greg\Desktop\brandon\iceVision\labels"
    rename_txt_files(folder)
