// Shim to use browser's built-in EventSource instead of the Node.js 'eventsource' package
export const EventSource = globalThis.EventSource || window.EventSource;
