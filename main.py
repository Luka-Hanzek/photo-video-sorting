import os
import argparse
import exiftool
import datetime
import shutil
import typing


LOGS_DIRECTORY = "logs"
script_run_timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


def get_creation_date(*, metadata: dict = None, file_path: str = None) -> typing.Optional[datetime.date]:
    POSSIBLE_TAGS = (
        "EXIF:CreateDate",
        "EXIF:DateTimeOriginal",
        "QuickTime:CreateDate",
        "QuickTime:MediaCreateDate",
    )

    if metadata is None and file_path is None:
        raise ValueError("Supply at least one argument.")

    if metadata is None:
        with exiftool.ExifToolHelper() as et:
            try:
                metadata = et.get_metadata(file_path)[0]
            except (TypeError, exiftool.exceptions.ExifToolExecuteError):
                return None
    if metadata is None:
        return None

    create_date_str = None
    for possible_tag in POSSIBLE_TAGS:
        if possible_tag in metadata:
            create_date_str = metadata[possible_tag]
            break

    if create_date_str is None:
        return None

    date_format = "%Y:%m:%d %H:%M:%S"

    return datetime.datetime.strptime(create_date_str, date_format)


def validate_move_arg(arg) -> bool:
    if arg == "False":
        return False
    elif arg == "True":
        return True
    else:
        raise ValueError("Invalid \"--move\" value.")


def get_files(dir_path: str) -> dict:
    all_file_paths = []
    for dirpath, dirnames, filenames in os.walk(dir_path):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            all_file_paths.append(full_path)

    files_metadata = []
    try:
        with exiftool.ExifTool() as et:
            files_metadata = et.execute_json(*all_file_paths)
    except exiftool.exceptions.ExifToolExecuteError:
        pass

    files = {}
    for file_path, metadata in zip(all_file_paths, files_metadata):
        files[file_path] = metadata

    return files


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--src", required=True)
    arg_parser.add_argument("--dest", required=True)
    arg_parser.add_argument("--move", default=False, action="store_true")

    args = arg_parser.parse_args()

    copy_or_move = shutil.move if args.move else shutil.copy

    os.makedirs(args.dest, exist_ok=True)

    files_with_metadata = get_files(args.src)
    files_to_move = {}

    for file_path, metadata in files_with_metadata.items():
        # Some files could no longer exists because related files have been also moved.
        if not os.path.exists(file_path):
            continue

        if metadata.get("File:MIMEType", "").startswith("video"):
            file_name = os.path.basename(file_path)
            create_date = get_creation_date(metadata=metadata)
            if create_date is None:
                print(f"Couldn't get creation date for file: {file_path}")

            # Destination directory name
            if create_date is not None:
                folder_name = create_date.strftime('%Y-%m-%d')
            else:
                folder_name = "no-date"
            dest_folder = os.path.join(args.dest, "video", folder_name)
            files_to_move[file_path] = os.path.join(dest_folder, file_name)
        elif (
                metadata.get("File:MIMEType", "").startswith("image")
                and metadata.get("File:FileTypeExtension", "").lower() in ("jpg", "jpeg", "arw", "png", "tiff")
            ):
            file_name = os.path.basename(file_path)
            create_date = get_creation_date(metadata=metadata)
            if create_date is None:
                print(f"Couldn't get creation date for file: {file_path}")

            # Destination directory name
            if create_date is not None:
                folder_name = create_date.strftime('%Y-%m-%d')
            else:
                folder_name = "no-date"
            dest_folder = os.path.join(args.dest, "image", folder_name)
            files_to_move[file_path] = os.path.join(dest_folder, file_name)

            # Also copy other extensions
            extensions_to_check = [
                "xmp",
                "dng",
                "arw",
            ]
            extensions_to_check.extend([ext.upper() for ext in extensions_to_check])

            ext_paths = [f"{os.path.splitext(file_path)[0]}.{ext}" for ext in extensions_to_check]
            ext_paths.extend([f"{file_path}.{ext}" for ext in extensions_to_check])

            ext_path_dir = os.path.dirname(file_path)
            potential_files = {os.path.join(ext_path_dir, filename) for filename in os.listdir(ext_path_dir)}

            for ext_path in ext_paths:
                if ext_path in potential_files:
                    files_to_move[ext_path] = os.path.join(dest_folder, os.path.basename(ext_path))

    for file_path, dest in files_to_move.items():
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        if os.path.exists(dest):
            print(f"{file_path} already exists.")
        else:
            # Copy the media
            print(f"{'Moving' if args.move else 'Copying'} {file_path}")
            copy_or_move(file_path, dest)
    
    unknown_files = set(files_with_metadata.keys()).difference(set(files_to_move.keys()))

    if unknown_files:
        os.makedirs(os.path.join(LOGS_DIRECTORY, script_run_timestamp), exist_ok=True)

        print("Skipped files:")
        for file_path in unknown_files:
            print(f"Unknown file: {file_path}")
            
            with open(os.path.join(LOGS_DIRECTORY, script_run_timestamp, "skipped"), "a") as f:
                print(file_path, file=f)
