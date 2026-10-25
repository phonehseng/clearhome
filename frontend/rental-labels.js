/* Keep the offered space and payment basis consistent in cards and lease help. */
window.ClearHouseRental = Object.freeze({
  period(row) {
    if (row.rental_space === 'room') return row.rent_basis === 'per_person_installment' ? ' / person / installment' : ' / person / month';
    return row.rental_space === 'entire_home' ? ' / apartment / month' : ' / month';
  },
  price(row) {
    return typeof row.monthly_rent === 'number' && Number.isFinite(row.monthly_rent)
      ? `From $${row.monthly_rent.toLocaleString('en-US',{maximumFractionDigits:0})}${this.period(row)}` : 'Rent: confirm with provider';
  },
  term(row) {
    const date = value => /^\d{4}-\d{2}-\d{2}$/.test(value || '')
      ? new Date(value + 'T12:00:00').toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'}) : '';
    return row.lease_start ? `Advertised term: ${date(row.lease_start)}${row.lease_end ? ' – ' + date(row.lease_end) : ''}`
      : row.lease_term_notes || (row.rental_space ? 'Lease dates: confirm with provider' : '');
  },
  space(row) {
    if (row.rental_space === 'room') return `One bedroom${row.shared_home_bedrooms ? ` in a ${row.shared_home_bedrooms}-bedroom shared home` : ' in a shared home'}`;
    return row.rental_space === 'entire_home' ? 'Whole apartment · price covers the entire home' : '';
  },
  lease(row) {
    return ({individual:'Individual bedroom agreement', joint:'Joint lease · responsibility for full apartment rent', confirm:'Lease responsibility: confirm with provider'})[row.lease_type] || '';
  }
});

/* A tel: link for a phone as written in the catalog. Only the first real number is dialed, so
   "(703) 792-3366 (TTY: 711)" doesn't become 7037923366711; an extension waits for the call to connect. */
window.ClearHouseDial = phone => {
  const text = String(phone || '');
  const m = text.match(/(\+?1[\s.-]?)?\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})(?:\s*(?:ext\.?|extension|x)\s*(\d{1,6}))?/i);
  if (m) return `tel:+1${m[2]}${m[3]}${m[4]}${m[5] ? ',' + m[5] : ''}`;
  const short = text.match(/^\s*(\d{3})\b/);  // 211, 911, 988
  return short ? 'tel:' + short[1] : 'tel:' + text.replace(/[^0-9+]/g, '');
};
