import test from 'node:test';
import assert from 'node:assert/strict';
import { paddingForFit, fallbackExtent, AUTOZOOM_PADDING_BOTTEN } from '../src/karta-logik.mjs';

test('paddingForFit: panel öppen ger 460 px höger padding (panelbredd + marginal)', () => {
  assert.deepEqual(paddingForFit(true), [40, 460, 336, 40]);
});

test('paddingForFit: panel ihopfälld ger bara 40 px höger padding (fliken)', () => {
  assert.deepEqual(paddingForFit(false), [40, 40, 336, 40]);
});

test('paddingForFit: botten-padding clearar biografi-stripen (296 px) + marginal', () => {
  const [, , botten] = paddingForFit(true);
  assert.equal(botten, AUTOZOOM_PADDING_BOTTEN);
  assert.ok(botten > 296, 'botten-padding måste vara större än stripens höjd');
});

test('fallbackExtent: 80 m-ruta centrerad på klickpunkten', () => {
  assert.deepEqual(fallbackExtent([1000, 2000]), [960, 1960, 1040, 2040]);
});
