# documents/utils.py

import hashlib


def hash_file(file_obj):
    """
    Generates SHA-256 hash of a file.
    Reads in chunks to handle large files without loading all into memory.
    """
    sha256 = hashlib.sha256()
    for chunk in file_obj.chunks():
        sha256.update(chunk)
    return sha256.hexdigest()