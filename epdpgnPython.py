# Save this file as create_epd.py
import chess.pgn
import time
import argparse
import os
import multiprocessing
from typing import Optional, List, Set, Tuple

# tqdm is a great library for progress bars. Install with: pip install tqdm
try:
    from tqdm import tqdm
except ImportError:
    print("Warning: 'tqdm' library not found. Progress bar will not be shown.")
    print("Install it with: pip install tqdm")
    # Create a dummy tqdm so the script doesn't crash
    def tqdm(iterable, **kwargs):
        return iterable

def _create_epd_id_string(game: chess.pgn.Game) -> str:
    """Creates a detailed EPD 'id' opcode for traceability."""
    white = game.headers.get("White", "?").replace('"', '\\"')
    black = game.headers.get("Black", "?").replace('"', '\\"')
    date = game.headers.get("Date", "????.??.??").replace('.', '-')
    eco = game.headers.get("ECO", "?")
    return f'id "{eco} {date} {white} vs {black}";'

def process_game_chunk(args: Tuple) -> None:
    """
    Worker function to process a list of game offsets from a PGN file.
    This function is executed by each process in the multiprocessing pool.
    It writes its findings to a temporary file to conserve memory.
    """
    pgn_input_file, offsets, temp_output_file, min_ply, max_ply, min_elo, target_eco_prefix = args
    
    local_unique_positions = set()
    
    with open(pgn_input_file, 'r', encoding='utf-8') as pgn:
        for offset in offsets:
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

def main():
    parser = argparse.ArgumentParser(
        description="Create a thematic EPD test suite from a large PGN database using multiprocessing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("pgn_input_file", help="Path to the input PGN file.")
    parser.add_argument(
        "-o", "--output", default="output_positions.epd",
        help="Name of the final EPD output file."
    )
    parser.add_argument(
        "-s", "--min-ply", type=int, default=1,
        help="The starting ply (half-move) to capture positions from."
    )
    parser.add_argument(
        "-m", "--max-ply", type=int, default=40,
        help="The maximum ply (half-move) to capture positions up to (e.g., 40 = end of move 20)."
    )
    parser.add_argument(
        "-e", "--elo", type=int, default=2400,
        help="Minimum Elo of both players to include a game. Set to 0 to disable."
    )
    parser.add_argument(
        "-c", "--eco", type=str, default=None,
        help="Filter for an ECO prefix (e.g., 'B' for Sicilian, 'D' for QG). Leave empty for no filter."
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=None,
        help="Number of worker processes to use. Defaults to the number of CPU cores."
    )
    args = parser.parse_args()

    if args.min_ply > args.max_ply:
        print("FATAL ERROR: --min-ply cannot be greater than --max-ply.")
        return

    num_workers = args.workers if args.workers is not None else os.cpu_count()
    if num_workers is None:
        num_workers = 1
    
    print(f"🚀 Starting EPD creation from '{args.pgn_input_file}'...")
    print(f"   - Ply Range: {args.min_ply} to {args.max_ply}")
    print(f"   - Minimum ELO: {args.elo}")
    print(f"   - ECO Prefix: '{args.eco or 'Any'}'")
    print(f"   - Using {num_workers} worker processes.")

    start_time = time.time()

    try:
        with open(args.pgn_input_file, 'r', encoding='utf-8') as pgn:
            print("   ...scanning PGN file to find game offsets (this may take a moment)...")
            offsets = list(chess.pgn.scan_offsets(pgn))
    except FileNotFoundError:
        print(f"FATAL ERROR: Input file not found at '{args.pgn_input_file}'")
        return
    
    total_games = len(offsets)
    if total_games == 0:
        print("No games found in PGN file.")
        return
    
    print(f"   ...found {total_games:,} games. Distributing work to workers...")

    # Split offsets into chunks for each worker
    chunk_size = (total_games + num_workers - 1) // num_workers
    chunks = [offsets[i:i + chunk_size] for i in range(0, total_games, chunk_size)]
    
    # Create temporary file paths for each worker
    temp_files = [f"{args.output}.{i}.tmp" for i in range(len(chunks))]

    # Prepare arguments for each worker, including the temp file path
    worker_args = [
        (args.pgn_input_file, chunks[i], temp_files[i], args.min_ply, args.max_ply, args.elo, args.eco)
        for i in range(len(chunks))
    ]

    unique_positions = set()
    
    try:
        with multiprocessing.Pool(processes=num_workers) as pool:
            with tqdm(total=len(chunks), desc="Processing Chunks") as pbar:
                # imap_unordered is good to get progress as chunks finish
                for _ in pool.imap_unordered(process_game_chunk, worker_args):
                    pbar.update(1)

        print("\n✅ Processing complete. Merging temporary files...")

        # --- Final Merge Step (Memory-Efficient) ---
        with tqdm(total=len(temp_files), desc="Merging Files") as pbar:
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            unique_positions.add(line.strip())
                pbar.update(1)

        print(f"\n✅ Merge complete. Sorting and writing final output file...")
        with open(args.output, 'w', encoding='utf-8') as f:
            for epd_line in sorted(list(unique_positions)):
                f.write(epd_line + '\n')
    finally:
        print("   ...cleaning up temporary files...")
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    end_time = time.time()
    total_time = end_time - start_time
    print(f"✨ Success! Found {len(unique_positions):,} unique positions from {total_games:,} games.")
    print(f"   Results saved to '{args.output}'")
    print(f"   Total time: {total_time // 60:.0f} minutes, {total_time % 60:.2f} seconds.")

if __name__ == "__main__":
    # On Windows, multiprocessing needs this guard
    multiprocessing.freeze_support() 
    main()