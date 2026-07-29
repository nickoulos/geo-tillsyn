import test from 'node:test';
import assert from 'node:assert/strict';
import { narmasteAr, stegAr, tickPosition } from '../src/tidslinje-logik.mjs';

const YEARS = [1960, 1975, 1998, 1999, 2001, 2007, 2023];

test('narmasteAr snappar till närmaste tillgängliga årgång', () => {
  assert.equal(narmasteAr(YEARS, 1961), 1960);
  assert.equal(narmasteAr(YEARS, 1990), 1998);
  assert.equal(narmasteAr(YEARS, 2023), 2023);
});

test('stegAr klampar i ändarna', () => {
  assert.equal(stegAr(YEARS, 1960, -1), 1960);
  assert.equal(stegAr(YEARS, 1998, 1), 1999);
  assert.equal(stegAr(YEARS, 2023, 1), 2023);
});

test('tickPosition är proportionell mot årtal (ärliga luckor)', () => {
  assert.equal(tickPosition(YEARS, 1960), 0);
  assert.equal(tickPosition(YEARS, 2023), 100);
  assert.ok(Math.abs(tickPosition(YEARS, 1998) - (38 / 63) * 100) < 0.01);
});
