import multiprocessing
import os
import time
import logging
from pathlib import Path
import chess.pgn
import io
import tempfile

# Configure logging to file and console for detailed debugging
# This will create a `processor.log` file in the same directory.
log_file_path = Path(__file__).resolve().parent / "processor.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

# --- Globals for worker processes ---
# These are set by the pool initializer to avoid pickling issues, which was
# the cause of the silent crashes.
_worker_pause_event = None
_worker_stop_event = None

def init_worker(pause_event, stop_event):
    """Initializer for each worker process in the pool."""
    global _worker_pause_event, _worker_stop_event
    _worker_pause_event = pause_event
    _worker_stop_event = stop_event
    logging.info(f"Worker {os.getpid()} initialized.")

def worker_process(chunk_info, temp_dir, settings):
    """
    Processes a single chunk of work.
    Writes results to a unique temporary file.
    """
    pause_event = _worker_pause_event
    stop_event = _worker_stop_event
    worker_log = logging.getLogger(f"Worker-{os.getpid()}-{chunk_info['id']}")
    worker_log.info(f"Starting chunk {chunk_info['id']} at offset {chunk_info['offset']} for {chunk_info['num_games']} games.")

    # Get filter settings from the main process
    min_elo = settings.get('min_elo', 0)
    max_ply = settings.get('max_ply', 1000)
    eco_prefix = settings.get('eco_prefix', '')

    # The broad try/except block has been removed. If a fundamental error like a
    # file I/O issue occurs, we WANT the worker to fail hard so the main process
    # knows about it and can report the error correctly.
    with tempfile.NamedTemporaryFile(dir=temp_dir, mode='w', delete=False, suffix='.epd', encoding='utf-8') as tf:
        temp_file_path = tf.name
        positions_written = 0

        # Open in binary mode to allow seeking to byte offsets.
        with open(settings['input_file'], 'rb') as pgn_file_binary:
            pgn_file_binary.seek(chunk_info['offset'])

            # Wrap the binary handle in a text-mode reader. The chess library expects strings.
            # This resolves the TypeError that was causing the worker to fail.
            pgn_file_text = io.TextIOWrapper(pgn_file_binary, encoding='utf-8', errors='replace')

            for i in range(chunk_info['num_games']):
                if stop_event.is_set():
                    worker_log.warning("Stop event detected, terminating chunk processing.")
                    return None

                if pause_event.is_set():
                    worker_log.info("Pause event detected, waiting.")
                    while pause_event.is_set():
                        if stop_event.is_set():
                            worker_log.warning("Stop event detected during pause, terminating.")
                            return None
                        time.sleep(0.5)
                    worker_log.info("Resuming.")

                game = chess.pgn.read_game(pgn_file_text)
                if game is None:
                    worker_log.warning(f"Read_game returned None after {i} games, ending chunk early.")
                    break

                # --- Filtering and EPD Generation Logic ---
                # This inner try/except is kept, as it correctly handles
                # malformed game data without crashing the entire worker.
                try:
                    white_elo = int(game.headers.get("WhiteElo", 0))
                    black_elo = int(game.headers.get("BlackElo", 0))
                    game_eco = game.headers.get("ECO", "")

                    if (white_elo >= min_elo or black_elo >= min_elo) and game.end().ply() <= max_ply and game_eco.startswith(eco_prefix):
                        board = game.end()
                        id_str = f'id "? {game.headers.get("Date", "????.??.??")} {game.headers.get("White", "?")} vs {game.headers.get("Black", "?")}"'
                        tf.write(board.epd(id=id_str) + '\n')
                        positions_written += 1
                except (ValueError, AttributeError) as e:
                    worker_log.warning(f"Skipping malformed game or headers: {e}")
                    continue

        worker_log.info(f"Finished chunk {chunk_info['id']}. Wrote {positions_written} positions.")
        return temp_file_path

def _cleanup_temp_files(temp_files):
    """Helper to remove a list of temporary files."""
    logging.info(f"Cleaning up {len(temp_files)} temporary files.")
    for f in temp_files:
        if f and os.path.exists(f):
            try:
                os.remove(f)
                logging.info(f"Removed temporary file: {f}")
            except OSError as e:
                logging.error(f"Error removing temporary file {f}: {e}")

def _merge_files(temp_files, output_file, progress_callback, final_message):
    """Merges a list of temporary files into the final output file."""
    valid_temp_files = [f for f in temp_files if f and os.path.exists(f)]
    logging.info(f"Starting to merge {len(valid_temp_files)} temporary files into {output_file}")

    if not valid_temp_files:
        logging.warning("No temporary files to merge.")
        progress_callback({"status": "complete", "progress": 100, "message": "No data was processed.", "is_complete": True})
        return

    try:
        with open(output_file, 'wb') as out_f:
            for temp_file in sorted(valid_temp_files):
                logging.info(f"Merging {temp_file}")
                with open(temp_file, 'rb') as in_f:
                    out_f.write(in_f.read())

        logging.info(f"Successfully merged files into {output_file}")
        progress_callback({"status": "complete", "progress": 100, "message": final_message, "is_complete": True})

    except Exception as e:
        logging.error(f"An error occurred during file merging: {e}", exc_info=True)
        progress_callback({"status": "error", "message": f"Failed to merge temporary files: {e}", "is_complete": True})
    finally:
        # Always clean up temp files after attempting to merge
        _cleanup_temp_files(valid_temp_files)

def run_processing(settings, progress_callback, pause_event, stop_event, stop_save_flag):
    """Main processing function, designed to be run in a separate process."""
    main_log = logging.getLogger("MainProcess")
    main_log.info(f"Starting processing with settings: {settings}")

    # Create a dedicated temporary directory for this run for cleanliness
    temp_dir = tempfile.mkdtemp(prefix="pgn-processor-")
    main_log.info(f"Created temporary directory: {temp_dir}")

    try:
        # --- Real PGN Chunking Logic ---
        main_log.info(f"Scanning PGN file to create chunks: {settings['input_file']}")
        game_offsets = []
        try:
            # Use the python-chess library's fast offset scanner. This is the
            # most robust and performant way to find game start positions.
            with open(settings['input_file'], 'rb') as pgn_file:
                # Manually scan for game start markers to get reliable byte offsets.
                # This is more compatible with older versions of the python-chess
                # library that may not have the `scan_offsets` function.
                offset = pgn_file.tell()
                while line := pgn_file.readline():
                    if line.startswith(b'[Event '):
                        game_offsets.append(offset)
                    offset = pgn_file.tell()

        except FileNotFoundError:
            main_log.error(f"Input file not found: {settings['input_file']}")
            progress_callback({"status": "error", "message": f"Input file not found: {settings['input_file']}", "is_complete": True})
            return

        if not game_offsets:
            main_log.warning("No games found in PGN file.")
            progress_callback({"status": "complete", "message": "No games found in the PGN file.", "is_complete": True})
            return

        chunk_size_games = 2500  # Number of games per worker task
        chunks = []
        for i in range(0, len(game_offsets), chunk_size_games):
            chunk_offsets = game_offsets[i : i + chunk_size_games]
            chunks.append({'id': i // chunk_size_games, 'offset': chunk_offsets[0], 'num_games': len(chunk_offsets)})

        main_log.info(f"Created {len(chunks)} chunks of work from {len(game_offsets)} games.")

        # Use an initializer to share the events with the worker processes
        # This is more robust than passing them as arguments directly to the task.
        with multiprocessing.Pool(
            processes=settings.get('workers', 4),
            initializer=init_worker,
            initargs=(pause_event, stop_event)
        ) as pool:
            results = [pool.apply_async(worker_process, (chunk, temp_dir, settings)) for chunk in chunks]
            main_log.info("All processing tasks submitted to pool. Waiting for completion...")

            # Monitor progress until all tasks are done or a stop is signaled
            while not all(res.ready() for res in results):
                if stop_event.is_set():
                    main_log.info("Stop event received. Breaking from monitoring loop.")
                    break
                
                completed_count = sum(1 for res in results if res.ready())
                progress = (completed_count / len(results)) * 95  # 95% for processing, 5% for merge
                progress_callback({
                    "status": "paused" if pause_event.is_set() else "processing",
                    "progress": int(progress),
                    "message": f"Processed {completed_count}/{len(results)} chunks."
                })
                time.sleep(1)

            # --- Post-processing Logic ---
            # This logic correctly handles the three possible outcomes:
            # 1. Stopped by user.
            # 2. Finished with one or more worker errors.
            # 3. Finished successfully.

            main_log.info("Worker monitoring loop finished.")

            if stop_event.is_set():
                main_log.warning("Processing was stopped by user. Terminating worker pool.")
                pool.terminate()
                pool.join()
                
                # Get whatever results we can from tasks that finished before termination.
                temp_files = [res.get() for res in results if res.ready() and res.successful()]

                if stop_save_flag.value:
                    main_log.info("'Save on stop' is enabled. Merging partial results.")
                    final_message = f"Processing stopped. Partial results saved to {settings['output_file']}."
                    _merge_files(temp_files, settings['output_file'], progress_callback, final_message)
                else:
                    main_log.info("'Save on stop' is disabled. Discarding results.")
                    _cleanup_temp_files(temp_files)
                    progress_callback({"status": "stopped", "message": "Processing stopped and results discarded.", "is_complete": True})
            else: # Not stopped, so it's either a success or failure.
                pool.close()
                pool.join()
                main_log.info("All tasks have completed. Checking for worker success.")
                
                if not all(res.successful() for res in results):
                    main_log.error("One or more workers failed with an exception. Aborting.")
                    # Clean up any files that were successfully created before the failure.
                    successful_files = [res.get() for res in results if res.ready() and res.successful()]
                    _cleanup_temp_files(successful_files)
                    progress_callback({"status": "error", "message": "A worker process failed. Check logs for details.", "is_complete": True})
                else:
                    # All workers completed without exceptions.
                    main_log.info("All workers succeeded. Proceeding to merge files.")
                    temp_files = [res.get() for res in results]
                    final_message = f"Processing complete. EPD file saved to {settings['output_file']}."
                    _merge_files(temp_files, settings['output_file'], progress_callback, final_message)

    except Exception as e:
        main_log.error(f"An unhandled exception occurred in run_processing: {e}", exc_info=True)
        progress_callback({"status": "error", "message": f"A critical error occurred: {e}", "is_complete": True})
    finally:
        # Final cleanup of the temporary directory
        try:
            # This might not be empty if cleanup failed, so we use rmtree for robustness
            import shutil
            shutil.rmtree(temp_dir)
            main_log.info(f"Removed temporary directory: {temp_dir}")
        except OSError as e:
            main_log.warning(f"Could not remove temporary directory {temp_dir}: {e}")