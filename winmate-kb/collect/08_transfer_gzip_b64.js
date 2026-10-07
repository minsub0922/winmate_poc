window.__gz = async (obj) => { const s = JSON.stringify(obj); const cs = new Blob([s]).stream().pipeThrough(new CompressionStream('gzip'));
 const buf = new Uint8Array(await new Response(cs).arrayBuffer()); let bin=''; for (let i=0;i<buf.length;i+=0x8000) bin+=String.fromCharCode.apply(null, buf.subarray(i,i+0x8000));
 const b64 = btoa(bin); return 'WKBGZ1:' + s.length + ':' + b64.length + ':' + b64; };
const W=window.__wkb; await window.__gz({cats:W.cats, products:W.products, cardOrder:W.cardOrder, variants:W.variants, filters:W.filters, fetchedAt:W.startedAt, finishedAt:W.finishedAt})