import os

def gather_files_from_directory(root):
    files = []
    for file in os.listdir(root):
        built_path = os.path.join(root, file)
        if os.path.isdir(file):
            files.extend(gather_files_from_directory)
        else:
            files.append(file)
    return files