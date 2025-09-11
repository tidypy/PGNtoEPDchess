<script lang="ts">
  import { onMount } from 'svelte';
  import { open, save } from '@tauri-apps/api/dialog';

  let status = 'disconnected';
  let progress = 0;
  let logs: string[] = [];
  let pgnFilePath = '';
  let outputFile = 'output.epd';
  let minPly = 1;
  let maxPly = 40;
  let minElo = 2400;
  let ecoPrefix = '';
  let workers = navigator.hardwareConcurrency || 4;

  let socket: WebSocket;

  onMount(() => {
    // Read query parameters for initial values
    const urlParams = new URLSearchParams(window.location.search);
    pgnFilePath = urlParams.get('pgnFile') || pgnFilePath;
    outputFile = urlParams.get('outputFile') || outputFile;
    workers = parseInt(urlParams.get('workers') || '', 10) || workers;
    minElo = parseInt(urlParams.get('minElo') || '', 10) || minElo;
    maxPly = parseInt(urlParams.get('maxPly') || '', 10) || maxPly;

    socket = new WebSocket('ws://127.0.0.1:8000/ws');

    socket.onopen = () => {
      status = 'connected';
      logs = [...logs, 'Connected to backend'];
      // If PGN file is provided in URL, start processing automatically
      if (pgnFilePath) {
        startProcessing();
      }
    };

    socket.onclose = () => {
      status = 'disconnected';
      logs = [...logs, 'Disconnected from backend'];
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      status = data.status;
      progress = data.progress;
      logs = [...logs, data.message];
    };

    return () => {
      socket.close();
    };
  });

  async function selectPgnFile() {
    try {
      const result = await open({
        title: 'Select PGN File',
        multiple: false,
        filters: [{ name: 'PGN Files', extensions: ['pgn'] }],
      });
      if (result) {
        pgnFilePath = result as string;
      }
    } catch (e) {
      console.error("Could not open file dialog", e);
      alert("Selecting a file only works in the desktop app version.");
    }
  }

  async function selectOutputFile() {
    try {
      const result = await save({
        title: 'Select Output EPD File',
        defaultPath: outputFile,
        filters: [{ name: 'EPD Files', extensions: ['epd'] }],
      });
      if (result) {
        outputFile = result;
      }
    } catch (e) {
      console.error("Could not open save dialog", e);
      alert("Selecting an output file only works in the desktop app version.");
    }
  }

  async function startProcessing() {
    if (!pgnFilePath) {
      alert('Please select a PGN file.');
      return;
    }

    console.log("Starting processing with settings:", {
      pgn_input_file: pgnFilePath,
      output_file: outputFile,
      min_ply: minPly,
      max_ply: maxPly,
      min_elo: minElo,
      eco_prefix: ecoPrefix,
      workers: workers,
    });

    const settings = {
      pgn_input_file: pgnFilePath,
      output_file: outputFile,
      min_ply: minPly,
      max_ply: maxPly,
      min_elo: minElo,
      eco_prefix: ecoPrefix,
      workers: workers,
    };

    try {
      const response = await fetch('http://127.0.0.1:8000/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      });
      const data = await response.json();
      logs = [...logs, data.message];
      console.log("Response from backend:", data);
    } catch (error) {
      logs = [...logs, 'Error starting processing: ' + error];
      console.error("Error starting processing:", error);
    }
  }

  async function pauseProcessing() {
    await fetch('http://127.0.0.1:8000/pause', { method: 'POST' });
  }

  async function resumeProcessing() {
    await fetch('http://127.0.0.1:8000/resume', { method: 'POST' });
  }

  async function stopProcessing(save: boolean) {
    await fetch(`http://127.0.0.1:8000/stop?save=${save}`, { method: 'POST' });
  }
</script>

<div class="container mx-auto p-4">
  <h1 class="text-2xl font-bold mb-4">PGN to EPD Converter</h1>

  <div class="grid grid-cols-2 gap-4 mb-4">
    <div class="flex flex-col">
      <label for="pgn-file" class="block mb-2">PGN File</label>
      <div class="flex">
        <input type="text" id="pgn-file" bind:value={pgnFilePath} class="w-full p-2 border rounded-l" />
        <button on:click={selectPgnFile} class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded-r">
          Browse
        </button>
      </div>
      <p class="text-xs text-gray-500 mt-1">("Browse" only works in the desktop app)</p>
    </div>
    <div class="flex flex-col">
      <label for="output-file" class="block mb-2">Output File</label>
      <div class="flex">
        <input type="text" id="output-file" bind:value={outputFile} class="w-full p-2 border rounded-l" />
        <button on:click={selectOutputFile} class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded-r">
          Browse
        </button>
      </div>
      <p class="text-xs text-gray-500 mt-1">("Browse" only works in the desktop app)</p>
    </div>
    <div>
      <label for="min-ply" class="block mb-2">Min Ply</label>
      <input type="number" id="min-ply" bind:value={minPly} class="w-full p-2 border" />
    </div>
    <div>
      <label for="max-ply" class="block mb-2">Max Ply</label>
      <input type="number" id="max-ply" bind:value={maxPly} class="w-full p-2 border" />
    </div>
    <div>
      <label for="min-elo" class="block mb-2">Min ELO</label>
      <input type="number" id="min-elo" bind:value={minElo} class="w-full p-2 border" />
    </div>
    <div>
      <label for="eco-prefix" class="block mb-2">ECO Prefix</label>
      <input type="text" id="eco-prefix" bind:value={ecoPrefix} class="w-full p-2 border" />
    </div>
    <div>
      <label for="workers" class="block mb-2">Workers</label>
      <input type="number" id="workers" bind:value={workers} class="w-full p-2 border" />
    </div>
  </div>

  <div class="flex space-x-2 mb-4">
    <button on:click={startProcessing} disabled={status === 'running'} class="bg-blue-500 text-white px-4 py-2 rounded disabled:bg-gray-400">Start</button>
    <button on:click={pauseProcessing} disabled={status !== 'running'} class="bg-yellow-500 text-white px-4 py-2 rounded disabled:bg-gray-400">Pause</button>
    <button on:click={resumeProcessing} disabled={status !== 'paused'} class="bg-green-500 text-white px-4 py-2 rounded disabled:bg-gray-400">Resume</button>
    <button on:click={() => stopProcessing(true)} disabled={status !== 'running' && status !== 'paused'} class="bg-red-500 text-white px-4 py-2 rounded disabled:bg-gray-400">Stop & Save</button>
    <button on:click={() => stopProcessing(false)} disabled={status !== 'running' && status !== 'paused'} class="bg-red-700 text-white px-4 py-2 rounded disabled:bg-gray-400">Stop & Discard</button>
  </div>

  <div class="mb-4">
    <div class="w-full bg-gray-200 rounded-full">
      <div class="bg-blue-600 text-xs font-medium text-blue-100 text-center p-0.5 leading-none rounded-full" style="width: {progress}%">{progress}%</div>
    </div>
  </div>

  <div class="bg-gray-100 p-4 rounded h-64 overflow-y-auto">
    <h2 class="font-bold mb-2">Logs</h2>
    <ul>
      {#each logs as log}
        <li>{log}</li>
      {/each}
    </ul>
  </div>
</div>