import test from 'node:test';
import assert from 'node:assert/strict';
import { cssText, STYLE_ID } from '../src/styles.mjs';

test('stylesheet innehåller tokens och alla huvudkomponenter', () => {
  const css = cssText();
  for (const sel of ['--gt-accent', '--gt-panel-bredd', '.gt-panel', '.gt-kort', '.gt-biografi',
    '.gt-tab', '.gt-legend', '.gt-skelett', '.gt-osakerhet', '.gt-badge',
    '.gt-sektion', '.gt-rad', '.gt-panel__fot']) {
    assert.ok(css.includes(sel), `saknar ${sel}`);
  }
});

test('STYLE_ID är stabilt (idempotent injektion bygger på det)', () => {
  assert.equal(STYLE_ID, 'gt-styles');
});
