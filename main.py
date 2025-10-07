import os
import argparse
import exiftool
import datetime
import shutil
import itertools


LOGS_DIRECTORY = "logs"
script_run_timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


def get_creation_date(file_path: str):
    POSSIBLE_TAGS = (
        "EXIF:CreateDate",
        "EXIF:DateTimeOriginal",
        "QuickTime:CreateDate",
        "QuickTime:MediaCreateDate",
    )

    metadata = None
    with exiftool.ExifToolHelper() as et:
        try:
            metadata = et.get_metadata(file_path)[0]
        except (TypeError, exiftool.exceptions.ExifToolExecuteError):
            return None

    create_date_str = None
    for tag, key in itertools.product(POSSIBLE_TAGS, metadata.keys()):
        if tag == key:
            create_date_str = metadata[key]
            break
        
    if create_date_str is None:
        return None

    if "+" in create_date_str or "-" in create_date_str:
        if create_date_str[-3] == ':':
            create_date_str = create_date_str[:-3] + create_date_str[-2:]
        date_format = f"%Y:%m:%d %H:%M:%S%z"
    else:
        date_format = "%Y:%m:%d %H:%M:%S"
    try:
        date = datetime.datetime.strptime(create_date_str, date_format)
    except ValueError:
        return None
    return date


def validate_move_arg(arg) -> bool:
    if arg == "False":
        return False
    elif arg == "True":
        return True
    else:
        raise ValueError("Invalid \"--move\" value.")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--src", required=True)
    arg_parser.add_argument("--dest", required=True)
    arg_parser.add_argument("--move", default=False, action="store_true")

    args = arg_parser.parse_args()

    copy_or_move = shutil.move if args.move else shutil.copy

    os.makedirs(args.dest, exist_ok=True)
    os.makedirs(os.path.join(LOGS_DIRECTORY, script_run_timestamp), exist_ok=True)

    for dirpath, dirnames, filenames in os.walk(args.src):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            if not os.path.exists(full_path):
                continue

            if filename.lower().endswith(".mp4") or filename.lower().endswith(".mov"):
                create_date = get_creation_date(full_path)
                if create_date is None:
                    print(f"Couldn't get creation date for file: {full_path}")
                    

                # Destination directory name
                if create_date is not None:
                    folder_name = create_date.strftime('%Y-%m-%d')
                else:
                    folder_name = "no-date"
                dest_folder = os.path.join(args.dest, "video", folder_name)

                # Ensure destination directory exists
                os.makedirs(dest_folder, exist_ok=True)

                # Copy the media
                print(f"Moving {filename}")
                copy_or_move(full_path, os.path.join(dest_folder, filename))
            elif (filename.lower().endswith(".jpg")
                    or filename.lower().endswith(".png")
                    or filename.lower().endswith(".tif")
                    or filename.lower().endswith(".arw")
                    or filename.lower().endswith(".dng")
                    or filename.lower().endswith(".jpeg")
                    ):
                create_date = get_creation_date(full_path)
                if create_date is None:
                    print(f"Couldn't get creation date for file: {full_path}")
            
                # Destination directory name
                if create_date is not None:
                    folder_name = create_date.strftime('%Y-%m-%d')
                else:
                    folder_name = "no-date"
                dest_folder = os.path.join(args.dest, "image", folder_name)
                    
                # Ensure destination directory exists
                os.makedirs(dest_folder, exist_ok=True)

                # Copy the media
                print(f"Moving {filename}")

                copy_or_move(full_path, os.path.join(dest_folder, filename))

                # Also copy other extensions
                extensions_to_check = [
                    "xmp",
                    "dng",
                    "arw",
                ]
                extensions_to_check.extend([ext.upper() for ext in extensions_to_check])

                full_paths = [f"{os.path.splitext(full_path)[0]}.{ext}" for ext in extensions_to_check]
                full_paths.extend([f"{full_path}.{ext}" for ext in extensions_to_check])

                for full_path in full_paths:
                    if os.path.exists(full_path):
                        print(f"Moving {full_path}")
                        copy_or_move(
                            full_path, os.path.join(dest_folder, os.path.basename(full_path))
                        )
            else:
                print(f"Unknown extension for file: {full_path}\n\tSkipping...")
                with open(os.path.join(LOGS_DIRECTORY, script_run_timestamp, "skipped"), "a") as f:
                    print(full_path, file=f)
