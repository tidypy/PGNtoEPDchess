export const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set([]),
	mimeTypes: {},
	_: {
		client: {"start":"_app/immutable/entry/start.05c085c2.js","app":"_app/immutable/entry/app.ad812aa5.js","imports":["_app/immutable/entry/start.05c085c2.js","_app/immutable/chunks/scheduler.e108d1fd.js","_app/immutable/chunks/singletons.8b4f7df1.js","_app/immutable/entry/app.ad812aa5.js","_app/immutable/chunks/scheduler.e108d1fd.js","_app/immutable/chunks/index.e9311cfd.js"],"stylesheets":[],"fonts":[]},
		nodes: [
			__memo(() => import('./nodes/0.js')),
			__memo(() => import('./nodes/1.js')),
			__memo(() => import('./nodes/2.js'))
		],
		routes: [
			{
				id: "/",
				pattern: /^\/$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			}
		],
		matchers: async () => {
			
			return {  };
		}
	}
}
})();
