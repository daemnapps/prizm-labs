// textboxes.swift — every line of words macOS Vision reads in a picture, with where it sits.
// One line each: "<left> <top> <width> <height>\t<text>", all 0-1 of the picture, top-left origin.
import Foundation
import Vision
import AppKit
guard CommandLine.arguments.count > 1,
      let img = NSImage(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(2) }
let r = VNRecognizeTextRequest(); r.recognitionLevel = .accurate; r.usesLanguageCorrection = false
try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([r])
for o in r.results ?? [] {
    guard let t = o.topCandidates(1).first else { continue }
    let b = o.boundingBox
    print(String(format: "%.4f %.4f %.4f %.4f", b.minX, 1 - b.maxY, b.width, b.height) + "\t" + t.string)
}
