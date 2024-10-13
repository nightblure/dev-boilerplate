import glob
import os
import shutil
from datetime import datetime

"""
NEED TO ADD TO alembic.ini !!!

file_template = %%(year)d-%%(month).2d-%%(day).2d_%%(slug)s
"""

FOLDER_PATH = "/Users/ivan/Desktop/work/pixi/pixi/migrations/versions"
# '/Users/ivan/Desktop/work/train_api/train_api/migrations/versions'
MATCH_PATTERN = "Create Date"


def get_migration_paths(folder_path) -> list[str]:
    return glob.glob(folder_path + "/*.py")


def extract_creation_date_from_migration_file(filepath) -> datetime:
    fmt = "%Y-%m-%d %H:%M:%S.%f"
    with open(filepath) as file:
        for line in file:
            if MATCH_PATTERN not in line:
                continue

            datetime_str = line.split(": ")[1].strip()
            return datetime.strptime(datetime_str, fmt)


def main():
    paths = get_migration_paths(FOLDER_PATH)
    filtered_paths = [p for p in paths if "__init__" not in p]

    print(f"Find {len(filtered_paths)} migration files")
    print("")
    renamed_files_folder = os.path.join(
        FOLDER_PATH, "renamed migrations " + str(datetime.now())
    )
    os.mkdir(renamed_files_folder)

    for path in filtered_paths:
        name = os.path.basename(path)
        path = os.path.join(FOLDER_PATH, name)
        creation_date = extract_creation_date_from_migration_file(path)

        if creation_date is None:
            print(f"DATE NOT FOUND IN FILE {name}")
            continue

        new_name = f"{creation_date.date()}_{name}"
        new_path = os.path.join(renamed_files_folder, new_name)
        shutil.copy2(path, new_path)
        print(name, " -> ", new_name)


main()
