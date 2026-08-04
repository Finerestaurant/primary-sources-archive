/* 호버 카드 — 링크에 머물면 그 문서의 요약을 미리 보여 준다.
 *
 *   <a href="cairo-1943/#d309" data-card="cairo-1943:d309">…</a>
 *   그리고 HoverCard.init(CARDS) 를 부른다.
 *
 * CARDS 는 { "문서철:문서id": {…} } 꼴이다. 값의 항목은 전부 없어도 된다 —
 * 없는 줄은 통째로 빠진다.
 *
 *   { title, date, route, sum, points: [], pages: 3, badge }
 *
 * 화면 밖으로 나가지 않게 자리를 잡고, 키보드 초점에도 뜬다.
 * 손가락으로 쓰는 기기(hover: none)에서는 CSS 가 카드를 감춘다 — 링크는 그대로다.
 */
window.HoverCard = (function () {
  var DATA = {}, el = null, cur = null, showT = 0, hideT = 0;
  var DELAY = 260, HIDE = 140;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function ensure() {
    if (el) return el;
    el = document.createElement('div');
    el.className = 'hc';
    el.setAttribute('role', 'tooltip');
    document.body.appendChild(el);
    return el;
  }

  function html(d) {
    var pts = (d.points || []).slice(0, 2).map(function (p) {
      return '<li>' + esc(p) + '</li>';
    }).join('');
    return '<div class="hc-top"><span>' + esc(d.date || '날짜 미상') + '</span>' +
             (d.badge ? '<span class="id">' + esc(d.badge) + '</span>' : '') +
           '</div>' +
           '<h4>' + esc(d.title || '') + '</h4>' +
           (d.route ? '<p class="hc-route">' + esc(d.route) + '</p>' : '') +
           (d.sum ? '<p class="sum">' + esc(d.sum) + '</p>' : '') +
           (pts ? '<ul>' + pts + '</ul>' : '') +
           (d.go === false && !d.pages ? '' :
             '<div class="hc-foot"><span>' +
               (d.pages ? esc(d.pages) + '면' : '') +
             '</span>' +
             (d.go === false ? '' : '<span class="go">눌러서 원문 보기 →</span>') +
             '</div>');
  }

  /* 링크 옆에 놓되 화면 밖으로 나가지 않게 민다. 위아래는 공간이 넓은 쪽으로. */
  function place(a) {
    var r = a.getBoundingClientRect();
    var w = el.offsetWidth, h = el.offsetHeight, m = 12;
    var top = r.bottom + 8;
    if (top + h > innerHeight - m && r.top - h - 8 > m) top = r.top - h - 8;
    top = Math.max(m, Math.min(top, innerHeight - h - m));
    var left = Math.min(r.left, innerWidth - w - m);
    el.style.top = top + 'px';
    el.style.left = Math.max(m, left) + 'px';
  }

  function show(a) {
    var d = DATA[a.dataset.card];
    if (!d) return;
    ensure();
    el.innerHTML = html(d);
    el.style.visibility = 'hidden';
    el.setAttribute('data-open', '');
    place(a);                    // 크기를 잰 뒤에 자리를 잡아야 한다
    el.style.visibility = '';
    cur = a;
  }

  function hide() {
    if (!el) return;
    el.removeAttribute('data-open');
    cur = null;
  }

  function bind(a) {
    function enter() {
      clearTimeout(hideT);
      clearTimeout(showT);
      showT = setTimeout(function () { show(a); }, DELAY);
    }
    function leave() {
      clearTimeout(showT);
      hideT = setTimeout(hide, HIDE);
    }
    a.addEventListener('mouseenter', enter);
    a.addEventListener('mouseleave', leave);
    a.addEventListener('focus', function () { clearTimeout(hideT); show(a); });
    a.addEventListener('blur', leave);
  }

  return {
    init: function (data, root) {
      // 덮어쓰지 않고 얹는다 — 본문 용어와 연대 바가 서로 다른 때에 init 을 부른다
      var add = data || {};
      for (var k in add) if (Object.prototype.hasOwnProperty.call(add, k)) DATA[k] = add[k];
      var scope = root || document;
      [].forEach.call(scope.querySelectorAll('[data-card]'), bind);
      addEventListener('scroll', function () { if (cur) place(cur); }, true);
      addEventListener('keydown', function (e) { if (e.key === 'Escape') hide(); });
    },
    hide: hide
  };
})();
