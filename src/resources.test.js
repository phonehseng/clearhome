import test from 'node:test';
import assert from 'node:assert/strict';
import { verifiedResources, filterResources, reviewText } from './resources.js';
const fixture = (extra = {}) => ({id:'test', name:'Test fixture — not a real listing', address:'Northern Virginia', type:'affordable_listing', monthly_rent:800, source_url:'https://example.org', verified:true, last_verified:'2026-10-01', ...extra});
test('recommendations require a manual verification record and source', () => {
  assert.equal(verifiedResources([fixture(), fixture({last_verified:null}), fixture({source_url:'javascript:alert(1)'}), fixture({verified:false})]).length, 1);
});
test('budget and accessibility filters never infer unknown data', () => {
  const items = [fixture(), fixture({id:'accessible',accessible:true}),fixture({id:'unknown-rent',monthly_rent:undefined})];
  assert.equal(filterResources(items,{budget:900}).length,2);
  assert.deepEqual(filterResources(items,{budget:900,accessible:true}).map(r=>r.id),['accessible']);
  assert.equal(filterResources(items,{location:'Alexandria'}).length,0);
});
test('emergency results put urgent verified resources first', () => {
  const items = [fixture({id:'regular',type:'emergency_shelter'}),fixture({id:'urgent',type:'emergency_shelter',urgent:true}),fixture({id:'unverified',type:'emergency_shelter',urgent:true,verified:false})];
  assert.deepEqual(filterResources(items,{type:'emergency'}).map(r=>r.id),['urgent','regular']);
});
test('limited text checks flag risky payment and fee language', () => {
  assert.equal(reviewText('Pay with a gift card. This fee is non-refundable.').length,2);
  assert.equal(reviewText('A bright room with a window.').length,0);
});
