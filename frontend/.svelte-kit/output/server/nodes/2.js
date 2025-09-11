

export const index = 2;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/2.bec126bb.js","_app/immutable/chunks/scheduler.e108d1fd.js","_app/immutable/chunks/index.e9311cfd.js"];
export const stylesheets = [];
export const fonts = [];
