from pathlib import Path

def is_image_file(path:Path) -> bool:
    return path.suffix in [".gif",".png",".jpg",".jpeg"]

def is_record_file(path:Path) -> bool:
    return path.suffix in [".mp3",".wav",".ogg"]

def is_video_file(path:Path) -> bool:
    return path.suffix in [".mp4",".avi",".flv",".wmv",".mov",".mpg",".mpeg"]

def is_file(type:str,path:Path) -> bool:
    if type == "image":
        return is_image_file(path)
    elif type == "record":
        return is_record_file(path)
    elif type == "video":
        return is_video_file(path)
    else:
        return False

def replace_message(msg:str,path:Path) -> str:
    return msg.replace("{filename}",path.name) \
            .replace("{filestem}",path.stem)