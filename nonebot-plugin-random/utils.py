from pathlib import Path

def is_image_file(path:Path) -> bool:
    return path.suffix in [".gif",".png",".jpg"]

def is_record_file(path:Path) -> bool:
    return path.suffix in [".mp3",".wav",".ogg"]

def is_file(type:str,path:Path) -> bool:
    if type == "image":
        return is_image_file(path)
    elif type == "record":
        return is_record_file(path)