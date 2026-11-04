// News フィルタと Publications フィルタ（JS が無くても全件表示される）
(function () {
  function press(group, btn) {
    group.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', b === btn ? 'true' : 'false'); });
  }

  // ---- News
  document.querySelectorAll('[data-filter-group="news"]').forEach(function (group) {
    var list = group.closest('section, .page').querySelector('.news-list');
    group.addEventListener('click', function (e) {
      var btn = e.target.closest('button'); if (!btn) return;
      press(group, btn);
      var k = btn.dataset.kind;
      list.querySelectorAll('.news-item').forEach(function (li) {
        li.hidden = !(k === 'all' || li.dataset.kind === k);
      });
    });
  });

  // ---- Publications
  var root = document.getElementById('pubs');
  if (!root) return;
  var filters = root.querySelector('.filters');
  filters.hidden = false;
  var state = { cat: 'all', fy: 'all', proj: 'all', q: '' };
  var tabs = filters.querySelector('.tabs');
  var years = filters.querySelector('.years');
  var proj = document.getElementById('f-proj');
  var q = document.getElementById('f-q');
  var empty = root.querySelector('.empty');

  // URL ハッシュ（#cat=journal&fy=2025）で状態を共有できるようにする
  function readHash() {
    location.hash.replace(/^#/, '').split('&').forEach(function (kv) {
      var p = kv.split('='); if (p.length === 2 && p[0] in state) state[p[0]] = decodeURIComponent(p[1]);
    });
  }
  function writeHash() {
    var parts = [];
    ['cat', 'fy', 'proj'].forEach(function (k) { if (state[k] !== 'all') parts.push(k + '=' + encodeURIComponent(state[k])); });
    history.replaceState(null, '', parts.length ? '#' + parts.join('&') : location.pathname);
  }
  function sync() {
    tabs.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.cat === state.cat ? 'true' : 'false'); });
    years.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.fy === String(state.fy) ? 'true' : 'false'); });
    proj.value = state.proj;
  }
  function apply() {
    var needle = state.q.trim().toLowerCase();
    var shown = 0;
    root.querySelectorAll('.pub-group').forEach(function (g) {
      var n = 0;
      var catOk = state.cat === 'all' || g.dataset.group === state.cat;
      g.querySelectorAll('.pub').forEach(function (li) {
        var ok = catOk &&
          (state.fy === 'all' || li.dataset.fy === String(state.fy)) &&
          (state.proj === 'all' || (' ' + li.dataset.proj + ' ').indexOf(' ' + state.proj + ' ') >= 0) &&
          (!needle || li.textContent.toLowerCase().indexOf(needle) >= 0);
        li.hidden = !ok; if (ok) n++;
      });
      g.hidden = n === 0;
      var c = g.querySelector('h2 .count'); if (c) c.textContent = n;
      shown += n;
    });
    empty.hidden = shown !== 0;
  }
  tabs.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; state.cat = b.dataset.cat; sync(); apply(); writeHash(); });
  years.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; state.fy = b.dataset.fy; sync(); apply(); writeHash(); });
  proj.addEventListener('change', function () { state.proj = proj.value; apply(); writeHash(); });
  q.addEventListener('input', function () { state.q = q.value; apply(); });
  readHash(); sync(); apply();
})();
