// faces.swift — print every face and every line of text in an image:
// "face x y w h" / "text x y w h" (0..1, top-left origin). macOS Vision, no install.
import Foundation
import Vision
import AppKit
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let img = NSImage(contentsOf: url), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(2) }
let faces = VNDetectFaceRectanglesRequest()
let text = VNRecognizeTextRequest(); text.recognitionLevel = .fast
try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([faces, text])
func out(_ k: String, _ b: CGRect) { print(String(format: "%@ %.4f %.4f %.4f %.4f", k, b.minX, 1 - b.maxY, b.width, b.height)) }
for f in faces.results ?? [] { out("face", f.boundingBox) }
for t in text.results ?? [] { out("text", t.boundingBox) }
