import threading
import time
from queue import Queue
from tqdm import tqdm


def thread_task(thread_id, total_iterations, progress_queue):
    for i in range(total_iterations):
        time.sleep(1)  # Simulate work
        progress_queue.put((thread_id, i))  # Put the progress update in the queue


def progress_bar_manager(num_threads, total_iterations):
    # Queue to receive progress updates
    progress_queue = Queue()

    # Start threads
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(
            target=thread_task, args=(i, total_iterations[i], progress_queue)
        )
        threads.append(thread)
        thread.start()

    # Initialize progress bars for each thread
    bars = [
        tqdm(total=total_iterations[i], desc=f"Thread-{i}", position=i)
        for i in range(num_threads)
    ]

    # Process progress updates
    total_work = sum(total_iterations)  # Total work to process across all threads
    for _ in range(total_work):
        thread_id, progress = progress_queue.get()
        bars[thread_id].update(1)  # Update the correct progress bar

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    # Close all progress bars
    for bar in bars:
        bar.close()


# Number of threads and total iterations per thread
num_threads = 5
total_iterations = [5, 4, 1, 2, 1]  # Total iterations for each thread

progress_bar_manager(num_threads, total_iterations)
