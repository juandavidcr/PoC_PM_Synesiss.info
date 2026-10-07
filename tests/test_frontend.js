const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup(responder){
  const elements = new Map();
  const requests = [];
  const storage = new Map();
  const buttons = Array.from({length: 56}, (_, index) => ({
    textContent: String(index + 1),
    classList: {toggle(){}},
  }));
  const document = {
    getElementById(id){
      if(!elements.has(id)) elements.set(id, {
        value: '', textContent: '', innerHTML: '', style: {}, checked: false,
        disabled: false, scrollIntoView(){},
      });
      return elements.get(id);
    },
    querySelector(){return null;},
    querySelectorAll(){return buttons;},
  };
  const context = vm.createContext({
    document, URLSearchParams, console, alert(){},
    localStorage: {
      getItem(key){return storage.get(key) ?? null;},
      setItem(key, value){storage.set(key, value);},
    },
    async fetch(url, options){
      requests.push({url, options});
      const result = await responder(url, options);
      return {
        ok: result.status ? result.status === 200 : true,
        status: result.status || 200,
        headers: {get(){return result.type || 'application/json';}},
        async json(){return result.data;},
        async text(){return result.text;},
      };
    },
  });
  for(const script of ['charts.js', 'verification.js', 'random.js', 'addData.js', 'agent.js']){
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/js', script), 'utf8'), context);
  }
  return {context, document, requests, storage};
}

async function main(){
  const prediction = setup(async url => ({data: url.startsWith('/api/predecir')
    ? [2, 3, 5, 4, 6].map(numero => ({numero, score: 0.7, frecuencia_h: 4, frecuencia_r: 2, brecha: 1}))
    : {suggestions: [{suggestion: [7, 8, 9, 10, 11, 6]}]},
  }));
  prediction.document.getElementById('cantidad-primos').value = '3';
  prediction.document.getElementById('cantidad-compuestos').value = '2';
  prediction.document.getElementById('ventana-pred').value = '50';
  await prediction.context.predecir();
  assert.match(prediction.document.getElementById('resultado-pred').innerHTML, /2 3 5 4 6 11/);
  assert.equal(prediction.requests.length, 2);

  const random = setup(async () => ({data: {suggestions: [{main: [2, 3, 4, 5, 6, 7], additional: 8, suggestion: [2, 3, 4, 5, 6, 7, 8]}]}}));
  await random.context.cargarAleatorio();
  assert.match(random.document.getElementById('aleatorio-result').innerHTML, /2 3 4 5 6 7 8/);
  const failedRandom = setup(async () => ({status: 400, data: {error: 'No hay datos disponibles'}}));
  await failedRandom.context.cargarAleatorio();
  assert.match(failedRandom.document.getElementById('aleatorio-result').innerHTML, /No hay datos disponibles/);

  const agent = setup(async (url, options) => {
    assert.equal(url, '/api/agente');
    const payload = JSON.parse(options.body);
    assert.deepEqual(payload.pool_primos, [2, 3, 5]);
    assert.deepEqual(payload.pool_compuestos, [4, 6, 8]);
    return {data: {
      main: [2, 3, 4, 5, 6, 8], additional: 7,
      primos: [2, 3, 5], compuestos: [4, 6, 8], ventana: 50, sorteos_analizados: 100,
      explicaciones: [2, 3, 4, 5, 6, 8].map(numero => ({numero, tipo: 'ejemplo', score: 0.5, frecuencia_h: 4, frecuencia_r: 2, brecha: 1})),
    }};
  });
  agent.document.getElementById('agente-primos').value = '3';
  agent.document.getElementById('agente-compuestos').value = '3';
  agent.document.getElementById('agente-ventana').value = '50';
  agent.document.getElementById('agente-pool-primos').value = '2,3,5';
  agent.document.getElementById('agente-pool-compuestos').value = '4,6,8';
  await agent.context.generarRecomendacionAgente();
  assert.match(agent.document.getElementById('agente-result').innerHTML, /2, 3, 4, 5, 6, 8/);
  assert.equal(agent.document.getElementById('agente-generar').disabled, false);
  agent.context.usarRecomendacionAgente();
  assert.deepEqual(Array.from(vm.runInContext('seleccionados', agent.context)), [2, 3, 4, 5, 6, 8]);
  const countBefore = agent.requests.length;
  agent.document.getElementById('agente-primos').value = '4';
  await agent.context.generarRecomendacionAgente();
  assert.match(agent.document.getElementById('agente-result').textContent, /debe sumar 6/);
  assert.equal(agent.requests.length, countBefore);

  const snapshot = 'CONCURSO,R1,R2,R3,R4,R5,R6,R7,FECHA\n101,2,3,4,5,6,7,8,07/10/2026\n';
  const bulk = setup(async (url, options) => {
    if(url === '/api/add_rows'){
      assert.equal(JSON.parse(options.body).lines.length, 2);
      return {data: {ok: true, added: 2}};
    }
    if(url === '/api/first_row') return {data: {CONCURSO: 9, FECHA: '01/10/2026'}};
    if(url === '/api/historic_csv') return {text: snapshot};
    if(url === '/api/sync_localstorage_csv'){
      assert.equal(JSON.parse(options.body).csv, snapshot);
      return {data: {ok: true, rows: 1}};
    }
    throw new Error('Unexpected URL: ' + url);
  });
  bulk.document.getElementById('input-bulk').value = '2,3,4,5,6,7 — 07/10/2026\n2,3,4,5,6,7,8 — 08/10/2026';
  await bulk.context.addRowsBulk();
  assert.match(bulk.document.getElementById('bulk-result').textContent, /2 sorteos añadidos/);
  assert.equal(bulk.document.getElementById('input-bulk').value, '');
  assert.equal(bulk.storage.get('modelo-numeric-historic-csv'), snapshot);
  assert.match(bulk.document.getElementById('sync-storage-status').textContent, /Sincronizado: 1/);
  bulk.context.localStorage.getItem = () => {throw new Error('Storage disabled');};
  const failedSync = await bulk.context.syncLocalStorageToCsv();
  assert.equal(failedSync.ok, false);
  assert.match(bulk.document.getElementById('sync-storage-status').textContent, /Storage disabled/);
  console.log('Frontend OK: predicción sin repetidos, aleatorio, agente, verificador, altas y sincronización.');
}

main().catch(error => {console.error(error); process.exitCode = 1;});
