/* Keep the offered space and payment basis consistent in cards and lease help. */
window.ClearHouseRental = Object.freeze({
  period(row) {
    if (row.rental_space === 'room') return row.rent_basis === 'per_person_installment' ? ' / person / installment' : ' / person / month';
    return row.rental_space === 'entire_home' ? ' / apartment / month' : ' / month';
  },
  price(row) {
    return typeof row.monthly_rent === 'number' && Number.isFinite(row.monthly_rent)
      ? `From $${row.monthly_rent.toLocaleString('en-US')}${this.period(row)}` : 'Rent: confirm with provider';
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
