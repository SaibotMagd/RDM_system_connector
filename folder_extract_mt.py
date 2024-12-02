import os
import multiprocessing
from multiprocessing import Queue
import time

# Function to list files in a directory
def list_files(directory, queue):
    """
    Walks through the directory and its subdirectories to list all files.
    Adds each file path to the queue after encoding to handle invalid surrogate characters.

    Args:
        directory (str): The root directory to start listing files from.
        queue (Queue): The queue to put the file paths into.
    """
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                # Filter out invalid surrogate characters
                file_path = file_path.encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')
                queue.put(file_path)
    except PermissionError as e:
        print(f"PermissionError: {e}")
    except Exception as e:
        print(f"Error: {e}")

# Function to write files to the output file
def write_files(queue, output_file):
    """
    Writes file paths from the queue to the output file.
    Stops writing when a None value is encountered in the queue.

    Args:
        queue (Queue): The queue to get the file paths from.
        output_file (str): The file to write the file paths to.
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        while True:
            file_path = queue.get()
            if file_path is None:
                break
            f.write(file_path + '\n')

# Main function
def main(root_directory, output_file, num_processes):
    """
    Coordinates the listing and writing of files using multiple processes.

    Args:
        root_directory (str): The root directory to start listing files from.
        output_file (str): The file to write the file paths to.
        num_processes (int): The number of processes to use for listing files.
    """
    queue = Queue()
    directories = [os.path.join(root_directory, d) for d in os.listdir(root_directory) if os.path.isdir(os.path.join(root_directory, d))]

    # Start the writer process
    writer_process = multiprocessing.Process(target=write_files, args=(queue, output_file))
    writer_process.start()

    # Start the worker processes
    processes = []
    for directory in directories:
        process = multiprocessing.Process(target=list_files, args=(directory, queue))
        process.start()
        processes.append(process)

    # Wait for all worker processes to finish
    for process in processes:
        process.join()

    # Signal the writer process to exit
    queue.put(None)
    writer_process.join()

if __name__ == "__main__":
    root_directory = '/home/cni/'
    output_file = '/home/filenames_py.txt'
    num_processes = 10  # Adjust the number of processes as needed

    start_time = time.time()
    main(root_directory, output_file, num_processes)
    end_time = time.time()

    print(f"Runtime: {end_time - start_time:.2f} seconds")
