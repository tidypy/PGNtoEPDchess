

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export const imports = ["_app/immutable/nodes/0.a1de8f2d.js","_app/immutable/chunks/scheduler.e108d1fd.js","_app/immutable/chunks/index.e9311cfd.js"];
export const stylesheets = ["_app/immutable/assets/0.3fa6a3ec.css"];
export const fonts = [];
