import os
import sqlite3
import concurrent.futures
import queue
import time
import timeit

def get_file_info(file_path):
    """
    Function to get file information.

    Args:
        file_path (str): The path to the file.

    Returns:
        tuple: A tuple containing the file path, size, creation time, and modification time.
    """
    stat = os.stat(file_path)
    return (
        file_path,
        stat.st_size,
        stat.st_ctime,
        stat.st_mtime,
    )

def process_folder(folder_path, file_queue):
    """
    Function to process files in a folder and put their information into a queue.

    Args:
        folder_path (str): The path to the folder to process.
        file_queue (queue.Queue): The queue to put file information into.

    This function walks through the folder and its subdirectories,
    gets the information for each file using get_file_info,
    and puts the information into the queue using a thread pool.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for root, dirs, files in os.walk(folder_path):
            futures.extend(executor.submit(file_queue.put, get_file_info(
                os.path.join(root, f))) for f in files)

        # Wait for all file processing tasks to complete
        concurrent.futures.wait(futures)

    # Add sentinel value to signal the end of file processing
    file_queue.put(None)

def save_to_database(file_queue, db_path):
    """
    Function to save file information from the queue to a SQLite database.

    Args:
        file_queue (queue.Queue): The queue to get file information from.
        db_path (str): The path to the SQLite database file.

    This function creates a SQLite database table if it does not exist,
    and continuously gets file information from the queue
    and inserts it into the database until a sentinel value (None) is encountered.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute('''CREATE TABLE "files" (
        "path"	text,
        "size"	INTEGER,
        "created"	TEXT,
        "modified"	TEXT
            );''')
    except:
        print("table already exists")

    while True:
        file_info = file_queue.get()
        if file_info is None:
            break
        # print(file_info)
        c.execute(
            'INSERT INTO files VALUES (?, ?, ?, ?)', file_info)

    conn.commit()
    conn.close()

def main(folder_path, db_path, worker):
    """
    Main function to coordinate the processing of files and saving to the database using multiple threads.

    Args:
        folder_path (str): The path to the folder to process.
        db_path (str): The path to the SQLite database file.
        worker (int): The number of worker threads to use.

    This function sets up a queue and starts a thread pool to process files and save their information to the database.
    """
    file_queue = queue.Queue()
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker) as executor:
        executor.submit(process_folder, folder_path, file_queue)
        executor.submit(save_to_database, file_queue, db_path)

if __name__ == '__main__':
    start_time = time.time()
    worker = 50
    main('/home/omero-import/',
         '/home/RDM_system_connector/data/fs_3tesla_extraction.db', worker)
    end_time = time.time()
    runtime = end_time - start_time
    print(f"worker: {worker} in {runtime}")
