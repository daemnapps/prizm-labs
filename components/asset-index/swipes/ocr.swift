import Foundation
import Vision
import AppKit
// ocr <image>... -> one JSON line per image: [{"t": text, "x","y","w","h" (0-1, top-left origin), "conf"}]
for path in CommandLine.arguments.dropFirst() {
  var out: [[String: Any]] = []
  if let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) {
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    for o in (req.results ?? []) {
      guard let c = o.topCandidates(1).first else { continue }
      let b = o.boundingBox
      out.append(["t": c.string, "x": b.minX, "y": 1 - b.maxY, "w": b.width, "h": b.height, "conf": c.confidence])
    }
  }
  let d = try! JSONSerialization.data(withJSONObject: out)
  print(String(data: d, encoding: .utf8)!)
}
