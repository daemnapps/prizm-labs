// Paste into the browser console on any product page (ours or a competitor's) at 1200 wide.
// Returns the layout numbers the page-look block checks: words, text styles, background
// colours down the page, page height, and what is in the first screen.
(() => {
  const main = document.querySelector('main') || document.body;
  const words = t => t.trim().split(/\s+/).filter(Boolean).length;
  const visible = [...main.querySelectorAll('h1,h2,h3,h4,p,li,span,button,a,dd,dt')]
    .filter(e => e.children.length === 0 && e.offsetHeight > 0);
  const styles = new Set(visible.filter(e => /^(H1|H2|H3|H4|P|LI)$/.test(e.tagName)).map(e => {
    const c = getComputedStyle(e); return `${c.fontFamily.split(',')[0]} ${c.fontSize} ${c.fontWeight}`; }));
  const bands = [...main.children].filter(e => e.offsetHeight > 80);
  const bgs = new Set(bands.map(e => getComputedStyle(e.firstElementChild || e).backgroundColor));
  const firstScreen = visible.filter(e => { const r = e.getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0; })
    .map(e => e.innerText.trim()).filter(Boolean).join(' · ').slice(0, 600);
  return { width: innerWidth, words: words(main.innerText), textStyles: styles.size, backgrounds: [...bgs],
           sections: bands.length, height: main.scrollHeight, firstScreen };
})();
