import chess.pgn
import time
import os
import multiprocessing
from typing import Optional, List, Set, Tuple, Dict, Any, Callable, TextIO

def _create_epd_id_string(game: chess.pgn.Game) -> str:
    """Creates a detailed EPD 'id' opcode for traceability."""
    white = game.headers.get("White", "?").replace('"', '\"')
    black = game.headers.get("Black", "?").replace('"', '\"')
    date = game.headers.get("Date", "????.??.??").replace('.', '-')
    eco = game.headers.get("ECO", "?")
    return f'id "{eco} {date} {white} vs {black}"'

def _get_game_offsets(pgn_file_handle: TextIO) -> List[int]:
    """
    Scans a PGN file for game offsets using chess.pgn.read_headers and skip_game.
    """
    offsets = []
    pgn_file_handle.seek(0)
    while True:
        offset = pgn_file_handle.tell()
        headers = chess.pgn.read_headers(pgn_file_handle)
        if headers is None:
            break
        offsets.append(offset)
        chess.pgn.skip_game(pgn_file_handle) # Skip the rest of the game
    pgn_file_handle.seek(0) # Reset file pointer for later processing
    return offsets

def process_game_chunk(args: Tuple) -> Tuple[str, int]:
    """
    Worker function to process a list of game offsets from a PGN file.
    This function is executed by each process in the multiprocessing pool.
    It writes its findings to a temporary file to conserve memory.
    Returns the path to the temporary file and the number of games processed.
    """
    pgn_input_file, offsets, temp_output_file, min_ply, max_ply, min_elo, target_eco_prefix, pause_event, stop_event = args
    
    local_unique_positions = set()
    games_processed_in_chunk = 0
    
    with open(pgn_input_file, 'r', encoding='utf-8') as pgn:
        for offset in offsets:
            if stop_event.is_set():
                break
            
            # Check pause/stop more frequently
            if pause_event.is_set():
                while pause_event.is_set():
                    time.sleep(0.1) # Sleep for a short duration to remain responsive
                    if stop_event.is_set():
                        break
                if stop_event.is_set(): # Check again after waking from pause
                    break

            pgn.seek(offset)
            try:
                game = chess.pgn.read_game(pgn)
                if game is None:
                    continue
            except (ValueError, RuntimeError):
                continue

            if target_eco_prefix and not game.headers.get('ECO', '?').startswith(target_eco_prefix):
                continue

            try:
                if min_elo > 0:
                     white_elo = int(game.headers.get('WhiteElo', '0'))
                     black_elo = int(game.headers.get('BlackElo', '0'))
                     if white_elo < min_elo or black_elo < min_elo:
                         continue
            except ValueError:
                continue

            id_str = _create_epd_id_string(game)
            node = game
            ply = 0
            while ply < max_ply:
                if stop_event.is_set(): # Check stop during ply iteration
                    break
                if pause_event.is_set(): # Check pause during ply iteration
                    while pause_event.is_set():
                        time.sleep(0.1)
                        if stop_event.is_set():
                            break
                    if stop_event.is_set():
                        break

                if node.is_end():
                    break
                
                node = node.variation(0)
                ply += 1

                if ply >= min_ply:
                    board = node.board()
                    fen = board.fen()
                    local_unique_positions.add(f"{fen} {id_str}")
            
            if stop_event.is_set(): # Check stop after ply iteration
                break

            games_processed_in_chunk += 1
    
    with open(temp_output_file, 'w', encoding='utf-8') as f:
        for epd_line in local_unique_positions:
            f.write(epd_line + '\n')
            
    return temp_output_file, games_processed_in_chunk

def run_processing(
    settings: Dict[str, Any],
    progress_callback: Callable[[Dict[str, Any]], None],
    pause_event: multiprocessing.Event,
    stop_event: multiprocessing.Event,
):
    """
    The main processing function.
    """
    temp_files = [] # Initialize here to ensure it's always defined for finally block
    try:
        pgn_input_file = settings['pgn_input_file']
        output_file = settings['output_file']
        min_ply = settings['min_ply']
        max_ply = settings['max_ply']
        min_elo = settings['min_elo']
        eco_prefix = settings['eco_prefix']
        num_workers = settings.get('workers', os.cpu_count() or 1)

        if min_ply > max_ply:
            progress_callback({"status": "error", "message": "min_ply cannot be greater than max_ply"})
            return

        progress_callback({"status": "running", "progress": 0, "message": f"Starting EPD creation from '{pgn_input_file}'..."})

        start_time = time.time()

        try:
            with open(pgn_input_file, 'r', encoding='utf-8') as pgn:
                progress_callback({"status": "running", "progress": 0, "message": "Scanning PGN file to find game offsets..."})
                offsets = _get_game_offsets(pgn)
        except FileNotFoundError:
            progress_callback({"status": "error", "message": f"Input file not found at '{pgn_input_file}'"})
            return
        
        total_games = len(offsets)
        if total_games == 0:
            progress_callback({"status": "complete", "progress": 100, "message": "No games found in PGN file."})
            return
        
        progress_callback({"status": "running", "progress": 0, "message": f"Found {total_games:,} games. Distributing work to workers..."})

        chunk_size = (total_games + num_workers - 1) // num_workers
        chunks = [offsets[i:i + chunk_size] for i in range(0, total_games, chunk_size)]
        
        temp_files = [f"{output_file}.{i}.tmp" for i in range(len(chunks))]

        worker_args = [
            (pgn_input_file, chunks[i], temp_files[i], min_ply, max_ply, min_elo, eco_prefix, pause_event, stop_event)
            for i in range(len(chunks))
        ]

        unique_positions = set()
        total_games_processed = 0
        
        with multiprocessing.Pool(processes=num_workers) as pool:
            completed_chunks = 0
            for temp_file, games_in_chunk in pool.imap_unordered(process_game_chunk, worker_args):
                if stop_event.is_set():
                    break
                completed_chunks += 1
                total_games_processed += games_in_chunk
                progress = int((total_games_processed / total_games) * 100)
                progress_callback({"status": "running", "progress": progress, "message": f"Processed {total_games_processed:,} of {total_games:,} games ({completed_chunks} chunks completed)"})

        if not stop_event.is_set():
            progress_callback({"status": "running", "progress": 100, "message": "Processing complete. Merging temporary files..."})

            try:
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        with open(temp_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                unique_positions.add(line.strip())
                        os.remove(temp_file) # Clean up temp file immediately after merging
            except Exception as merge_e:
                progress_callback({"status": "error", "message": f"Error during merge: {merge_e}"})
                return

            progress_callback({"status": "running", "progress": 100, "message": "Merge complete. Sorting and writing final output file..."})
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    for epd_line in sorted(list(unique_positions)):
                        f.write(epd_line + '\n')
            except Exception as write_e:
                progress_callback({"status": "error", "message": f"Error writing output file: {write_e}"})
                return

        end_time = time.time()
        total_time = end_time - start_time
        
        if stop_event.is_set():
             progress_callback({"status": "stopped", "progress": 0, "message": "Processing stopped by user."})
        else:
            progress_callback({
                "status": "complete", 
                "progress": 100, 
                "message": f"Success! Found {len(unique_positions):,} unique positions from {total_games:,} games. Results saved to '{output_file}'. Total time: {total_time // 60:.0f} minutes, {total_time % 60:.2f} seconds."
            })

    except Exception as e:
        progress_callback({"status": "error", "message": f"An unexpected error occurred: {e}"})
    finally:
        # This block will always execute, ensuring cleanup happens.
        progress_callback({"status": "running", "progress": 100, "message": "Cleaning up temporary files..."})
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
