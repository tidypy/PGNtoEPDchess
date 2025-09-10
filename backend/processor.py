import chess.pgn
import time
import os
import multiprocessing
from typing import Optional, List, Set, Tuple, Dict, Any, Callable

def _create_epd_id_string(game: chess.pgn.Game) -> str:
    """Creates a detailed EPD 'id' opcode for traceability."""
    white = game.headers.get("White", "?").replace('"', '\\"')
    black = game.headers.get("Black", "?").replace('"', '\\"')
    date = game.headers.get("Date", "????.??.??").replace('.', '-')
    eco = game.headers.get("ECO", "?")
    return f'id "{eco} {date} {white} vs {black}";'

def process_game_chunk(args: Tuple) -> str:
    """
    Worker function to process a list of game offsets from a PGN file.
    This function is executed by each process in the multiprocessing pool.
    It writes its findings to a temporary file to conserve memory.
    Returns the path to the temporary file.
    """
    pgn_input_file, offsets, temp_output_file, min_ply, max_ply, min_elo, target_eco_prefix, pause_event, stop_event = args
    
    local_unique_positions = set()
    
    with open(pgn_input_file, 'r', encoding='utf-8') as pgn:
        for offset in offsets:
            if stop_event.is_set():
                break
            if pause_event.is_set():
                # This is a simple way to pause. The worker will just sleep.
                # A more advanced implementation could involve more complex state management.
                while pause_event.is_set():
                    time.sleep(1)
                    if stop_event.is_set():
                        break

            pgn.seek(offset)
            try:
                game = chess.pgn.read_game(pgn)
                if game is None:
                    continue
            except (ValueError, RuntimeError): # Catch potential parsing errors
                continue

            # --- Apply filters ---
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

            # --- Advance game and capture positions within the specified ply range ---
            id_str = _create_epd_id_string(game)
            node = game
            ply = 0
            while ply < max_ply:
                if node.is_end():
                    break
                
                node = node.variation(0)
                ply += 1

                if ply >= min_ply:
                    board = node.board()
                    fen = board.fen()
                    local_unique_positions.add(f"{fen} {id_str}")
    
    # Write unique positions found in this chunk to its temporary file
    with open(temp_output_file, 'w', encoding='utf-8') as f:
        for epd_line in local_unique_positions:
            f.write(epd_line + '\n')
            
    return temp_output_file

def run_processing(
    settings: Dict[str, Any],
    progress_callback: Callable[[Dict[str, Any]], None],
    pause_event: multiprocessing.Event,
    stop_event: multiprocessing.Event,
):
    """
    The main processing function.
    """
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
            offsets = list(chess.pgn.scan_offsets(pgn))
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
    
    try:
        with multiprocessing.Pool(processes=num_workers) as pool:
            completed_chunks = 0
            for temp_file in pool.imap_unordered(process_game_chunk, worker_args):
                if stop_event.is_set():
                    break
                completed_chunks += 1
                progress = int((completed_chunks / len(chunks)) * 100)
                progress_callback({"status": "running", "progress": progress, "message": f"Processed chunk {completed_chunks} of {len(chunks)}"})

        if not stop_event.is_set():
            progress_callback({"status": "running", "progress": 100, "message": "Processing complete. Merging temporary files..."})

            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            unique_positions.add(line.strip())
            
            progress_callback({"status": "running", "progress": 100, "message": "Merge complete. Sorting and writing final output file..."})
            with open(output_file, 'w', encoding='utf-8') as f:
                for epd_line in sorted(list(unique_positions)):
                    f.write(epd_line + '\n')

    finally:
        progress_callback({"status": "running", "progress": 100, "message": "Cleaning up temporary files..."})
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

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
