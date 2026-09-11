/**
 * preload.js – Puente seguro entre main y renderer
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  fetchXML: (url) => ipcRenderer.invoke('fetch-xml', url),
});
