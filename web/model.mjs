export function matchRows(receipt, observations, kind) {
  if (!receipt) return [];
  return receipt.items.map(point => {
    const observed = observations[`${receipt.entity}|${point.target}`];
    const usable = observed && Number.isFinite(observed.value) && (kind !== 'tide' || observed.quality === '1') && (kind !== 'transit' || observed.value > Date.parse(receipt.captured_at)/1000);
    const value = usable ? observed.value : null;
    const error = value === null ? null : kind === 'transit' ? (value-point.value)/60 : point.value-value;
    const origin = receipt.provenance==='published_archive' ? receipt.issued_at : receipt.captured_at;
    return {...point, observed: value, evidence: usable ? observed : null, error, lead:(Date.parse(point.target_time || point.target)-Date.parse(origin))/3600000};
  });
}
export function statistics(rows) {
  const scored=rows.filter(r=>Number.isFinite(r.error));
  return {count:scored.length,total:rows.length,mae:scored.length?scored.reduce((n,r)=>n+Math.abs(r.error),0)/scored.length:null,bias:scored.length?scored.reduce((n,r)=>n+r.error,0)/scored.length:null};
}
export function csv(rows, kind) {
  const quote=value=>`"${String(value??'').replaceAll('"','""')}"`;
  const columns=['target','target_time','label','value','observed','error','lead'];
  return [columns.join(','),...rows.map(r=>columns.map(k=>quote(r[k])).join(','))].join('\r\n');
}
export function valueLabel(value, kind) {
  if (value===null || !Number.isFinite(value)) return 'Awaiting observation';
  if (kind==='transit') return new Date(value*1000).toISOString().slice(11,19)+' UTC';
  return new Intl.NumberFormat('en-CA',{maximumFractionDigits:kind==='tide'?3:0}).format(value);
}
export function groupReceipts(receipts) {
  return [...new Map(receipts.map(r=>[r.entity,r.label])).entries()].sort((a,b)=>a[1].localeCompare(b[1]));
}
