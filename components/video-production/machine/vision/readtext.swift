// readtext.swift — print every line of text Vision reads in an image, one per line.
// With --boxes: "<height 0-1>\t<confidence 0-1>\t<text>" per line, so callers can tell the big words from the small print.
import Foundation
import Vision
import AppKit
guard let img = NSImage(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(2) }
let boxes = CommandLine.arguments.contains("--boxes")
let r = VNRecognizeTextRequest(); r.recognitionLevel = .accurate
try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([r])
for o in r.results ?? [] {
    if let t = o.topCandidates(1).first {
        if boxes { print(String(format: "%.4f\t%.2f", o.boundingBox.height, t.confidence) + "\t" + t.string) } else { print(t.string) }
    }
}
