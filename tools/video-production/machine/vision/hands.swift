// hands.swift — every hand's joints in an image (macOS Vision hand pose, no install):
// "hand <n> <joint> x y confidence" per joint, 0..1, top-left origin.
// Used to read a product's real size off the hand holding it (product_kit.py).
import Foundation
import Vision
import AppKit
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let img = NSImage(contentsOf: url), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(2) }
let r = VNDetectHumanHandPoseRequest(); r.maximumHandCount = 4
try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([r])
let names: [(String, VNHumanHandPoseObservation.JointName)] = [
  ("wrist", .wrist), ("indexMCP", .indexMCP), ("middleMCP", .middleMCP), ("ringMCP", .ringMCP), ("littleMCP", .littleMCP),
  ("middleTip", .middleTip), ("thumbCMC", .thumbCMC)]
for (i, h) in (r.results ?? []).enumerated() {
  for (n, j) in names {
    if let p = try? h.recognizedPoint(j), p.confidence > 0.3 {
      print(String(format: "hand %d %@ %.4f %.4f %.2f", i, n, p.location.x, 1 - p.location.y, p.confidence))
    }
  }
}
