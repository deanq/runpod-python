''' Allows for the import of all modules in the utils directory. '''

from .rp_download import download_files_from_urls

from .rp_upload import upload_file_to_bucket, upload_in_memory_object


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
