<script lang="ts">
  import { onMount } from 'svelte';
  import io from 'socket.io-client';

  let status = 'disconnected';
  let progress = 0;
  let logs: string[] = [];
  let pgnFile: FileList;
  let outputFile = 'output.epd';
  let minPly = 1;
  let maxPly = 40;
  let minElo = 2400;
  let ecoPrefix = '';
  let workers = navigator.hardwareConcurrency || 4;

  let socket;

  onMount(() => {
    socket = io('ws://127.0.0.1:8000', {
      transports: ['websocket'],
    });

    socket.on('connect', () => {
      status = 'connected';
      logs = [...logs, 'Connected to backend'];
    });

    socket.on('disconnect', () => {
      status = 'disconnected';
      logs = [...logs, 'Disconnected from backend'];
    });

    socket.on('message', (data) => {
      status = data.status;
      progress = data.progress;
      logs = [...logs, data.message];
    });

    return () => {
      socket.disconnect();
    };
  });

  async function startProcessing() {
    if (!pgnFile || pgnFile.length === 0) {
      alert('Please select a PGN file.');
      return;
    }

    const settings = {
      pgn_input_file: pgnFile[0].path,
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
    } catch (error) {
      logs = [...logs, 'Error starting processing: ' + error];
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
    <div>
      <label for="pgn-file" class="block mb-2">PGN File</label>
      <input type="file" id="pgn-file" bind:files={pgnFile} class="w-full" />
    </div>
    <div>
      <label for="output-file" class="block mb-2">Output File</label>
      <input type="text" id="output-file" bind:value={outputFile} class="w-full p-2 border" />
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
