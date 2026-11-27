(function () {
  var SRT = "__SRT__";
  var p = app.project, seq = p.activeSequence;
  if (!seq) { for (var s = 0; s < p.sequences.numSequences; s++) { if (p.sequences[s].name.indexOf("brief-") >= 0) { p.openSequence(p.sequences[s].sequenceID); } } seq = p.activeSequence; }
  if (!seq) return "no sequence";
  for (var t0 = 0; t0 < seq.videoTracks.numTracks; t0++) { var tr0 = seq.videoTracks[t0]; for (var k0 = 0; k0 < tr0.clips.numItems; k0++) { var c0 = tr0.clips[k0]; if (c0.name.indexOf("Caption \u00b7") == 0 && c0.disabled) return "createCaptionTrack true (already in, kept as you left it)"; } }
  function find(bin) { for (var i = 0; i < bin.children.numItems; i++) { var c = bin.children[i]; if (c.type == 2) { var r = find(c); if (r) return r; } else if (c.name == "captions.srt") return c; } return null; }
  var item = find(p.rootItem);
  if (!item) { p.importFiles([SRT], true, p.rootItem, false); item = find(p.rootItem); }
  if (!item) return "srt not imported";
  var before = seq.captionTracks ? seq.captionTracks.numTracks : -1;
  var ok = seq.createCaptionTrack(item, 0, Sequence.CAPTION_FORMAT_SUBTITLE);
  var after = seq.captionTracks ? seq.captionTracks.numTracks : -1;
  var off = 0;
  for (var t = 0; t < seq.videoTracks.numTracks; t++) { var tr = seq.videoTracks[t]; for (var k = 0; k < tr.clips.numItems; k++) { var cl = tr.clips[k]; if (cl.name.indexOf("Caption ·") == 0) { cl.disabled = true; off++; } } }
  p.save();
  return "seq " + seq.name + " | createCaptionTrack " + ok + " | caption tracks " + before + " -> " + after + " | picture captions turned off " + off;
})();
