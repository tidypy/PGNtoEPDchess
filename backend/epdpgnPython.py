import argparse
import multiprocessing
import os
import sys

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from processor import run_processing

def console_progress_callback(status):
    """A simple callback to print progress to the console."""
    print(f"[{status.get('status', '').upper()}] {status.get('progress', '')}% - {status.get('message', '')}")

def main():
    parser = argparse.ArgumentParser(
        description="Create a thematic EPD test suite from a large PGN database.",
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

    settings = {
        'pgn_input_file': args.pgn_input_file,
        'output_file': args.output,
        'min_ply': args.min_ply,
        'max_ply': args.max_ply,
        'min_elo': args.elo,
        'eco_prefix': args.eco,
        'workers': args.workers,
    }

    # Create dummy events for the command-line version
    pause_event = multiprocessing.Event()
    stop_event = multiprocessing.Event()

    run_processing(settings, console_progress_callback, pause_event, stop_event)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
