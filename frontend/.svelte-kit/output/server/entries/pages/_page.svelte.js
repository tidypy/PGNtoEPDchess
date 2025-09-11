import { c as create_ssr_component, d as add_attribute, e as escape, f as each } from "../../chunks/ssr.js";
import "@tauri-apps/api/dialog";
const Page = create_ssr_component(($$result, $$props, $$bindings, slots) => {
  let progress = 0;
  let logs = [];
  let pgnFilePath = "";
  let outputFile = "output.epd";
  let minPly = 1;
  let maxPly = 40;
  let minElo = 2400;
  let ecoPrefix = "";
  let workers = navigator.hardwareConcurrency || 4;
  return `<div class="container mx-auto p-4"><h1 class="text-2xl font-bold mb-4" data-svelte-h="svelte-15gemix">PGN to EPD Converter</h1> <div class="grid grid-cols-2 gap-4 mb-4"><div class="flex flex-col"><label for="pgn-file" class="block mb-2" data-svelte-h="svelte-r8e5q9">PGN File</label> <div class="flex"><input type="text" id="pgn-file" class="w-full p-2 border rounded-l"${add_attribute("value", pgnFilePath, 0)}> <button class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded-r" data-svelte-h="svelte-m0pepn">Browse</button></div> <p class="text-xs text-gray-500 mt-1" data-svelte-h="svelte-1y48u6">(&quot;Browse&quot; only works in the desktop app)</p></div> <div class="flex flex-col"><label for="output-file" class="block mb-2" data-svelte-h="svelte-klxbfd">Output File</label> <div class="flex"><input type="text" id="output-file" class="w-full p-2 border rounded-l"${add_attribute("value", outputFile, 0)}> <button class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded-r" data-svelte-h="svelte-ihz0kr">Browse</button></div> <p class="text-xs text-gray-500 mt-1" data-svelte-h="svelte-1y48u6">(&quot;Browse&quot; only works in the desktop app)</p></div> <div><label for="min-ply" class="block mb-2" data-svelte-h="svelte-1qgwzrz">Min Ply</label> <input type="number" id="min-ply" class="w-full p-2 border"${add_attribute("value", minPly, 0)}></div> <div><label for="max-ply" class="block mb-2" data-svelte-h="svelte-116nzmf">Max Ply</label> <input type="number" id="max-ply" class="w-full p-2 border"${add_attribute("value", maxPly, 0)}></div> <div><label for="min-elo" class="block mb-2" data-svelte-h="svelte-ngaygv">Min ELO</label> <input type="number" id="min-elo" class="w-full p-2 border"${add_attribute("value", minElo, 0)}></div> <div><label for="eco-prefix" class="block mb-2" data-svelte-h="svelte-1k11kvh">ECO Prefix</label> <input type="text" id="eco-prefix" class="w-full p-2 border"${add_attribute("value", ecoPrefix, 0)}></div> <div><label for="workers" class="block mb-2" data-svelte-h="svelte-cactqk">Workers</label> <input type="number" id="workers" class="w-full p-2 border"${add_attribute("value", workers, 0)}></div></div> <div class="flex space-x-2 mb-4"><button ${""} class="bg-blue-500 text-white px-4 py-2 rounded disabled:bg-gray-400">Start</button> <button ${"disabled"} class="bg-yellow-500 text-white px-4 py-2 rounded disabled:bg-gray-400">Pause</button> <button ${"disabled"} class="bg-green-500 text-white px-4 py-2 rounded disabled:bg-gray-400">Resume</button> <button ${"disabled"} class="bg-red-500 text-white px-4 py-2 rounded disabled:bg-gray-400">Stop &amp; Save</button> <button ${"disabled"} class="bg-red-700 text-white px-4 py-2 rounded disabled:bg-gray-400">Stop &amp; Discard</button></div> <div class="mb-4"><div class="w-full bg-gray-200 rounded-full"><div class="bg-blue-600 text-xs font-medium text-blue-100 text-center p-0.5 leading-none rounded-full" style="${"width: " + escape(progress, true) + "%"}">${escape(progress)}%</div></div></div> <div class="bg-gray-100 p-4 rounded h-64 overflow-y-auto"><h2 class="font-bold mb-2" data-svelte-h="svelte-1qxymfj">Logs</h2> <ul>${each(logs, (log) => {
    return `<li>${escape(log)}</li>`;
  })}</ul></div></div>`;
});
export {
  Page as default
};
