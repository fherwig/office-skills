// Runs in the when2meet page world. Marks each block as ONE rectangle drag (one SaveTimes POST each).
// Uses the page's own SelectStop(), so the site computes and saves the availability string itself.
var BLOCKS = __BLOCKS__; var report = [];
(async function () {
  for (var k = 0; k < BLOCKS.length; k++) {
    var els = BLOCKS[k].map(function (t) { return document.getElementById('YouTime' + t); });
    var ok = els.filter(function (e) { return e; });
    if (!ok.length) { report.push({ block: k, error: 'no cells' }); continue; }
    var cols = ok.map(function (e) { return +e.getAttribute('data-col'); });
    var rows = ok.map(function (e) { return +e.getAttribute('data-row'); });
    if (Math.min.apply(null, cols) !== Math.max.apply(null, cols)) { report.push({ block: k, error: 'spans columns' }); continue; }
    FromCol = ToCol = cols[0]; FromRow = Math.min.apply(null, rows); ToRow = Math.max.apply(null, rows);
    ChangeToAvailable = true; IsMouseDown = true; SelectStop(); IsMouseDown = false;
    report.push({ block: k, cells: ok.length, missing: els.length - ok.length });
    await new Promise(function (r) { setTimeout(r, 400); });
  }
  ReColorIndividual(); if (typeof ReColorGroup === 'function') ReColorGroup();
  document.body.setAttribute('data-fill', JSON.stringify({
    marked: AvailableAtSlot.filter(function (a) { return a.indexOf(UserID) >= 0; }).length, report: report }));
})();
