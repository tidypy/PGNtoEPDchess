

export const index = 1;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/fallbacks/error.svelte.js')).default;
export const imports = ["_app/immutable/nodes/1.4e595897.js","_app/immutable/chunks/scheduler.e108d1fd.js","_app/immutable/chunks/index.e9311cfd.js","_app/immutable/chunks/singletons.8b4f7df1.js"];
export const stylesheets = [];
export const fonts = [];
