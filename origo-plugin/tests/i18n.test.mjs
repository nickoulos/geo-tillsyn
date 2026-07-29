import test from 'node:test';
import assert from 'node:assert/strict';
import { TEXTS, FALT_LABEL, faltLabel, formatTal, teckenTal } from '../src/i18n.mjs';

test('sv och en har exakt samma nycklar', () => {
  assert.deepEqual(Object.keys(TEXTS.en).sort(), Object.keys(TEXTS.sv).sort());
  assert.deepEqual(Object.keys(FALT_LABEL.en).sort(), Object.keys(FALT_LABEL.sv).sort());
});

test('checkTitel finns för alla tre kontroller på båda språken', () => {
  for (const sprak of ['sv', 'en']) {
    for (const key of ['olovligt', 'lovavvikelse', 'strandskydd']) {
      assert.equal(typeof TEXTS[sprak].checkTitel[key], 'string');
      assert.equal(typeof TEXTS[sprak].checkUndertitel[key], 'string');
    }
  }
});

test('faltLabel: känd nyckel översätts, okänd faller tillbaka till nyckeln', () => {
  assert.equal(faltLabel('area_diff_m2', 'sv'), 'Areaavvikelse');
  assert.equal(faltLabel('area_diff_m2', 'en'), 'Area difference');
  assert.equal(faltLabel('helt_okand_nyckel', 'sv'), 'helt_okand_nyckel');
});

test('formatTal: svensk decimalkomma, engelsk punkt, max en decimal', () => {
  assert.equal(formatTal(90.3, 'sv'), '90,3');
  assert.equal(formatTal(90.3, 'en'), '90.3');
  assert.equal(formatTal(38.42, 'sv'), '38,4');
  assert.equal(formatTal(15, 'sv'), '15');
});

test('teckenTal: plus-prefix på positiva, minus följer med negativa', () => {
  assert.equal(teckenTal(90.3, 'sv'), '+90,3');
  assert.equal(teckenTal(-4.2, 'sv'), '-4,2');
  assert.equal(teckenTal(0, 'sv'), '0');
});

test('rubrik-funktionerna komponerar neutrala rubriker', () => {
  const t = TEXTS.sv;
  assert.equal(t.rubrikOlovligt(1998, 2001), 'Uppförd 1998–2001 enligt ortofoto');
  assert.equal(t.rubrikOlovligtRegister(1999), 'nybyggnadsår 1999 i registret');
  assert.equal(t.rubrikAvvikelse('+90,3', '+38,4'), '+90,3 m² (+38,4 %) mot godkänt lov');
  assert.equal(t.rubrikStrandskydd(2, 5), '2 av 5 byggnader berör strandskyddszon');
});
