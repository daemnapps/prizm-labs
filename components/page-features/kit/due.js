/* components/page-features/kit/due.js — QB-10 (queue colours): the emails page's due-date rule, carried by other
   pages whole between their two due.js markers, the way act.js is. Component-owned, never edited per page.

   The rule is emails.html's urgOf / dueTag exactly (the template and editor's page, 2026-10-29), not a new one:
   2 days or less "d-red" (#F9B7D0 on #9A1A55), 5 or less "d-yel" (#FBE8A6 on #7A5800), more "d-grn" (#BCD9F6 on
   #1A4F85); the words "Due <Day, Mon D> · <in N days | tomorrow | today>", past the date "Overdue · was due <Day,
   Mon D>"; nothing when there is no date or the work is done. Days count from local noon to local noon, as there.
   test_qb10_queue_colours.py runs this file and both emails pages over the same dates and fails on any difference.

   pfDue.tag(date, done) -> a <span class="pill due d-…"> or null · pfDue.urg(date, done) -> "red" | "yel" | "grn" | ""
   pfDue.day(date), pfDue.away(date) -> the words, as the emails page's DAY and AWAY say them.
*/
(function (w) {
  function days(d) { var t = new Date(d + "T12:00:00"), n = new Date(); n.setHours(12, 0, 0, 0); return Math.round((t - n) / 864e5); }
  function day(d) {
    if (!d) return "no day yet";
    var t = new Date(d + "T12:00:00");
    return isNaN(t) ? d : t.toLocaleDateString("en-US", {weekday: "short", month: "short", day: "numeric"});
  }
  function away(d) { if (!d) return ""; var k = days(d); return k < 0 ? "sent" : k === 0 ? "today" : k === 1 ? "tomorrow" : "in " + k + " days"; }
  function urg(d, done) { if (!d || done) return ""; var k = days(d); return k <= 2 ? "red" : k <= 5 ? "yel" : "grn"; }
  function tag(d, done) {
    if (!d || done) return null;
    var k = days(d), s = w.document.createElement("span");
    s.className = "pill due " + (k <= 2 ? "d-red" : k <= 5 ? "d-yel" : "d-grn");
    s.textContent = away(d) === "sent" ? "Overdue · was due " + day(d) : "Due " + day(d) + " · " + away(d);
    return s;
  }
  w.pfDue = {tag: tag, urg: urg, day: day, away: away};
})(window);
