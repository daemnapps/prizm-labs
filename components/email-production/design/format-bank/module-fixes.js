// Cosmetic fixes for materialized Figma modules (LinkCTA underline position, footer unsubscribe block)
(function () {
  var tries = 0;
  var t = setInterval(function () {
    var done = false;
    var spans = Array.prototype.slice.call(document.querySelectorAll('span'));
    spans.forEach(function (s) {
      var txt = (s.textContent || '').trim();
      if ((txt === 'READ MORE' || txt === 'LOAD MORE') && !s.__fixed) {
        s.__fixed = true; done = true;
        s.style.top = '0px';
        var clip = s.parentElement;
        if (clip) { clip.style.height = '32px'; clip.style.clipPath = 'none';
          var ov = clip.parentElement; if (ov) ov.style.height = '32px';
          var root = ov && ov.parentElement; if (root && root.style) root.style.height = '32px';
          Array.prototype.slice.call(clip.children).forEach(function (ch) {
            if (ch.tagName === 'DIV' && ch.offsetHeight === 2) ch.style.top = '24px';
          });
        }
      }
      if (txt.indexOf('No longer want to receive') === 0 && !s.__fixed) {
        s.__fixed = true; done = true;
        var blk = s.parentElement;
        if (blk) { blk.style.height = 'auto'; blk.style.minHeight = '94px'; }
      }
    });
    if (++tries > 50 || (done && tries > 8)) clearInterval(t);
  }, 300);
})();
