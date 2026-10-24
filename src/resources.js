// A resource must carry a completed manual verification record before display.
export function verifiedResources(resources) {
  const types = { affordable_listing: 'housing', housing_authority: 'housing', rental_assistance: 'housing', emergency_shelter: 'emergency' };
  return resources.filter(r => r.id && r.name && r.address && types[r.type] &&
    r.verified === true && Number.isFinite(Date.parse(r.last_verified)) &&
    /^https:\/\//.test(r.source_url || '') && !/PLACEHOLDER|REPLACE/i.test(r.name + r.address))
    .map(r => ({...r, type: types[r.type], location: r.address,
      description: [r.who_it_serves, r.cost, r.requirements].filter(Boolean).join(' · '),
      monthlyRent: r.monthly_rent, wheelchairAccessible: r.accessible,
      sourceUrl: r.source_url, verification: { verifiedAt: r.last_verified }}));
}
export function filterResources(resources, { location = '', budget = '', accessible = false, type = 'housing' } = {}) {
  return verifiedResources(resources)
    .filter(r => r.type === type && r.location.toLowerCase().includes(location.trim().toLowerCase()))
    .filter(r => type !== 'housing' || ((!budget || (typeof r.monthlyRent === 'number' && r.monthlyRent <= Number(budget))) && (!accessible || r.wheelchairAccessible === true)))
    .sort((a, b) => Number(Boolean(b.urgent)) - Number(Boolean(a.urgent)));
}
export function reviewText(text) {
  const checks = [
    [/wire transfer|western union|gift card|cryptocurrency|bitcoin/i, 'Unusual payment request', 'Requests for wire transfers, gift cards, or cryptocurrency can be scam warning signs. Verify the property and recipient before sending money.'],
    [/before (a |the )?(viewing|tour)|without (a |the )?(viewing|tour)|sight unseen/i, 'Payment or commitment before a viewing', 'Ask to see the property and verify who has authority to rent it before paying or signing.'],
    [/waiv\w*.{0,50}(rights|liability)|not liable/i, 'Rights or liability language', 'This language may limit protections or shift responsibility. Ask a local tenant advocate to explain how it applies.'],
    [/non.?refundable|penalty|late fee|automatic.{0,15}renew/i, 'Fees or renewal terms', 'Check the amount, timing, cancellation process, and whether these terms are allowed in your area.'],
    [/immediately|today only|act now|urgent deposit/i, 'Pressure to act quickly', 'Take time to verify the listing independently. Urgency alone does not prove a scam.'],
  ];
  return checks.filter(([pattern]) => pattern.test(text)).map(([, title, explanation]) => ({title, explanation}));
}
