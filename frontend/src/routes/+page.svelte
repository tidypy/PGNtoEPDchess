<script>
	import { onMount } from 'svelte';
	import { writable } from 'svelte/store';
	import { open, save } from '@tauri-apps/api/dialog';

	// --- State Management ---
	// A central store for the application's current status.
	// Possible values: 'idle', 'processing', 'paused', 'stopping', 'complete', 'error', 'stopped'
	const status = writable('idle');
	const progress = writable(0);
	const logs = writable([]);
	const showStopModal = writable(false);

	// Store for all user-configurable settings
	const settings = writable({
		inputFile: '',
		outputFile: '',
		minElo: 2000,
		maxPly: 40,
		ecoPrefix: '',
		workers: navigator.hardwareConcurrency || 4
	});

	// --- WebSocket Connection ---
	function connectWebSocket() {
		const ws = new WebSocket('ws://127.0.0.1:8000/ws');

		ws.onopen = () => {
			addLog('WebSocket connection established.');
		};

		ws.onmessage = (event) => {
			const message = JSON.parse(event.data);

			// Update state based on messages from the backend
			if (message.status) {
				status.set(message.status);
			}
			if (message.progress != null) {
				progress.set(message.progress);
			}
			if (message.message) {
				addLog(message.message);
			}

			// If the process is finished, update status accordingly
			if (message.is_complete) {
				if (message.status === 'complete' || message.status === 'stopped' || message.status === 'error') {
					status.set(message.status);
				}
			}
		};

		ws.onclose = () => {
			addLog('WebSocket disconnected. Attempting to reconnect in 3 seconds...');
			// Don't try to reconnect if the user is idle or the job is done
			if (!['idle', 'complete', 'stopped', 'error'].includes($status)) {
				setTimeout(connectWebSocket, 3000);
			}
		};

		ws.onerror = (error) => {
			console.error('WebSocket error:', error);
			addLog('WebSocket error. See console for details.');
			ws.close();
		};
	}

	// --- Lifecycle & Initial State ---
	onMount(async () => {
		// Read test parameters from the URL query string on page load.
		// This makes the start_dev.sh script more useful.
		const urlParams = new URLSearchParams(window.location.search);
		const pgnFile = urlParams.get('pgnFile');
		const outFile = urlParams.get('outputFile');
		const workers = urlParams.get('workers');
		const minElo = urlParams.get('minElo');
		const maxPly = urlParams.get('maxPly');
		settings.update((s) => ({
			...s,
			inputFile: pgnFile || s.inputFile,
			outputFile: outFile || s.outputFile,
			workers: workers ? parseInt(workers, 10) : s.workers,
			minElo: minElo ? parseInt(minElo, 10) : s.minElo,
			maxPly: maxPly ? parseInt(maxPly, 10) : s.maxPly
		}));

		// When the app loads, check if a process is already running.
		try {
			const res = await fetch('http://127.0.0.1:8000/status');
			if (res.ok) {
				const initialState = await res.json();
				status.set(initialState.status);
				if (initialState.status !== 'idle') {
					addLog('Reconnected to an ongoing process.');
				}
			} else {
				throw new Error('Backend not reachable');
			}
		} catch (e) {
			status.set('error');
			addLog('Error: Could not connect to the backend server.');
		}

		connectWebSocket();
	});

	// --- UI Action Handlers ---
	async function selectPgnFile() {
		try {
			const selectedPath = await open({
				multiple: false,
				filters: [{ name: 'PGN Files', extensions: ['pgn'] }]
			});
			if (selectedPath && !Array.isArray(selectedPath)) {
				settings.update((s) => ({ ...s, inputFile: selectedPath }));
			}
		} catch (e) {
			console.error('Error opening file dialog:', e);
			alert(
				'File dialogs require the desktop app context.\n\nWhen developing in a browser, please paste the full file path into the input field manually.'
			);
		}
	}

	async function selectOutputFile() {
		try {
			const filePath = await save({
				filters: [{ name: 'EPD Files', extensions: ['epd'] }]
			});
			if (filePath) {
				settings.update((s) => ({ ...s, outputFile: filePath }));
			}
		} catch (e) {
			console.error('Error opening save dialog:', e);
			alert(
				'File dialogs require the desktop app context.\n\nWhen developing in a browser, please paste the full file path into the input field manually.'
			);
		}
	}

	async function handleStart() {
		if (!$settings.inputFile || !$settings.outputFile) {
			alert('Please select both an input and an output file.');
			return;
		}

		logs.set([]);
		addLog('Starting processing...');
		progress.set(0);
		status.set('processing');

		await fetch('http://127.0.0.1:8000/start', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify($settings)
		});
	}

	async function handlePause() {
		await fetch('http://127.0.0.1:8000/pause', { method: 'POST' });
	}

	async function handleResume() {
		await fetch('http://127.0.0.1:8000/resume', { method: 'POST' });
	}

	function handleStopClick() {
		showStopModal.set(true);
	}

	async function confirmStop(shouldSave) {
		showStopModal.set(false);
		status.set('stopping');
		addLog(shouldSave ? 'Stopping and saving partial results...' : 'Stopping and discarding results...');
		await fetch(`http://127.0.0.1:8000/stop?save=${shouldSave}`, { method: 'POST' });
	}

	function handleReset() {
		status.set('idle');
		progress.set(0);
		logs.set([]);
	}

	function addLog(message) {
		const timestamp = new Date().toLocaleTimeString();
		logs.update((l) => [`[${timestamp}] ${message}`, ...l]);
	}

	// --- Reactive UI variables ---
	$: isProcessing = ['processing', 'paused', 'stopping'].includes($status);
	$: isFinished = ['complete', 'stopped', 'error'].includes($status);
</script>

<main>
	<div class="container">
		<h1>PGN to EPD Converter</h1>

		<!-- Settings Panel -->
		<section class="panel settings-panel">
			<h2>Settings</h2>
			<div class="form-grid">
				<label for="input-file">Input PGN File</label>
				<div class="file-input">
					<input id="input-file" type="text" bind:value={$settings.inputFile} placeholder="Click Browse or paste a full path" />
					<button on:click={selectPgnFile} disabled={isProcessing}>Browse...</button>
				</div>

				<label for="output-file">Output EPD File</label>
				<div class="file-input">
					<input id="output-file" type="text" bind:value={$settings.outputFile} placeholder="Click Browse or paste a full path" />
					<button on:click={selectOutputFile} disabled={isProcessing}>Browse...</button>
				</div>

				<label for="workers">Worker Processes</label>
				<input id="workers" type="number" min="1" bind:value={$settings.workers} disabled={isProcessing} />
			</div>
		</section>

		<!-- Controls Panel -->
		<section class="panel controls-panel">
			<h2>Controls</h2>
			<div class="button-group">
				{#if !isProcessing && !isFinished}
					<button class="primary" on:click={handleStart}>Start Processing</button>
				{/if}

				{#if $status === 'processing'}
					<button on:click={handlePause}>Pause</button>
				{/if}

				{#if $status === 'paused'}
					<button on:click={handleResume}>Resume</button>
				{/if}

				{#if isProcessing}
					<button class="danger" on:click={handleStopClick}>Stop</button>
				{/if}

				{#if isFinished}
					<button class="primary" on:click={handleReset}>Run Again</button>
				{/if}
			</div>
		</section>

		<!-- Stop Confirmation Modal -->
		{#if $showStopModal}
			<div class="modal-backdrop" on:click={() => showStopModal.set(false)}>
				<div class="modal" on:click|stopPropagation>
					<h3>Stop Processing</h3>
					<p>Do you want to save the results processed so far?</p>
					<div class="modal-buttons">
						<button on:click={() => confirmStop(false)}>Discard & Stop</button>
						<button class="primary" on:click={() => confirmStop(true)}>Save & Stop</button>
					</div>
				</div>
			</div>
		{/if}

		<!-- Feedback Panel (Progress and Logs) -->
		{#if isProcessing || isFinished}
			<section class="panel feedback-panel">
				<h2>Status: {$status}</h2>
				<div class="progress-bar-container">
					<div class="progress-bar" style="width: {$progress}%" />
				</div>
				<span class="progress-text">{$progress}%</span>

				<h2>Logs</h2>
				<div class="log-panel">
					{#each $logs as log}
						<p>{log}</p>
					{/each}
				</div>
			</section>
		{/if}
	</div>
</main>

<style>
	:root {
		--bg-color: #282c34;
		--panel-bg: #353a44;
		--text-color: #abb2bf;
		--primary-color: #61afef;
		--danger-color: #e06c75;
		--border-color: #4f5666;
	}
	main {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
		background-color: var(--bg-color);
		color: var(--text-color);
		min-height: 100vh;
		padding: 2rem;
	}
	.container {
		max-width: 800px;
		margin: 0 auto;
	}
	.panel {
		background-color: var(--panel-bg);
		border: 1px solid var(--border-color);
		border-radius: 8px;
		padding: 1.5rem;
		margin-bottom: 1.5rem;
	}
	h1 { color: var(--primary-color); }
	h2 { border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; margin-top: 0; }
	.form-grid { display: grid; grid-template-columns: 150px 1fr; gap: 1rem; align-items: center; }
	.file-input { display: flex; }
	input {
		width: 100%;
		padding: 0.5rem;
		background-color: var(--bg-color);
		border: 1px solid var(--border-color);
		color: var(--text-color);
		border-radius: 4px;
	}
	.file-input input { border-right: none; border-top-right-radius: 0; border-bottom-right-radius: 0; }
	button {
		padding: 0.5rem 1rem;
		border: 1px solid var(--border-color);
		background-color: var(--panel-bg);
		color: var(--text-color);
		cursor: pointer;
		border-radius: 4px;
		transition: background-color 0.2s;
	}
	button:hover:not(:disabled) { background-color: #4f5666; }
	button:disabled { opacity: 0.5; cursor: not-allowed; }
	.file-input button { border-top-left-radius: 0; border-bottom-left-radius: 0; }
	.button-group { display: flex; gap: 1rem; }
	button.primary { background-color: var(--primary-color); color: #282c34; border-color: var(--primary-color); }
	button.danger { background-color: var(--danger-color); color: #282c34; border-color: var(--danger-color); }
	.progress-bar-container { width: 100%; background-color: var(--bg-color); border-radius: 4px; overflow: hidden; }
	.progress-bar { height: 20px; background-color: var(--primary-color); transition: width 0.3s ease-in-out; }
	.progress-text { margin-top: 0.5rem; display: block; text-align: center; }
	.log-panel {
		background-color: var(--bg-color);
		border-radius: 4px;
		padding: 1rem;
		height: 200px;
		overflow-y: auto;
		font-family: 'Courier New', Courier, monospace;
		font-size: 0.9em;
		display: flex;
		flex-direction: column-reverse; /* Shows newest logs at the bottom */
	}
	.log-panel p { margin: 0 0 0.25rem; }

	.modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background-color: rgba(0, 0, 0, 0.6);
		display: flex;
		justify-content: center;
		align-items: center;
		z-index: 100;
	}
	.modal {
		background-color: var(--panel-bg);
		padding: 2rem;
		border-radius: 8px;
		border: 1px solid var(--border-color);
		text-align: center;
		min-width: 300px;
		box-shadow: 0 5px 15px rgba(0,0,0,0.3);
	}
	.modal-buttons {
		margin-top: 1.5rem;
		display: flex;
		justify-content: center;
		gap: 1rem;
	}
</style>