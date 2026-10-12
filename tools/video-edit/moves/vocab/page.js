(function(){
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var vids = [].slice.call(document.querySelectorAll('video.clip'));
  function play(v){ var p = v.play(); if (p && p.catch) p.catch(function(){}); }
  if ('IntersectionObserver' in window){
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){
        var v = e.target;
        if (e.isIntersecting){ if (!reduce) play(v); }
        else if (!v.paused) v.pause();
      });
    }, {rootMargin:'120px 0px', threshold:0.15});
    vids.forEach(function(v){ io.observe(v); });
  } else if (!reduce){ vids.forEach(play); }
  vids.forEach(function(v){
    v.addEventListener('click', function(){ v.paused ? play(v) : v.pause(); });
  });

  var q = document.getElementById('q'), none = document.getElementById('none');
  var cards = [].slice.call(document.querySelectorAll('.card'));
  var groups = [].slice.call(document.querySelectorAll('.group'));
  var chips = [].slice.call(document.querySelectorAll('.chip'));
  function filter(){
    var s = q.value.trim().toLowerCase(), words = s.split(/\s+/).filter(Boolean), total = 0;
    cards.forEach(function(c){
      var h = c.getAttribute('data-hay');
      c.hidden = !words.every(function(w){ return h.indexOf(w) > -1; });
    });
    groups.forEach(function(g){
      var n = g.querySelectorAll('.card:not([hidden])').length; total += n;
      g.hidden = n === 0;
      var chip = document.querySelector('.chip[data-g="'+g.getAttribute('data-g')+'"]');
      if (chip){ chip.querySelector('b').textContent = n; chip.classList.toggle('dim', n === 0); }
    });
    none.hidden = total > 0;
  }
  q.addEventListener('input', filter);
  filter();

  if ('IntersectionObserver' in window){
    var gio = new IntersectionObserver(function(es){
      es.forEach(function(e){
        if (e.isIntersecting){
          var k = e.target.getAttribute('data-g');
          chips.forEach(function(c){ c.classList.toggle('on', c.getAttribute('data-g') === k); });
        }
      });
    }, {rootMargin:'-30% 0px -60% 0px'});
    groups.forEach(function(g){ gio.observe(g); });
  }
})();
