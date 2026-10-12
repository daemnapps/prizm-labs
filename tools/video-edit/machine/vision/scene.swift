// scene: what's in one picture, so words can be placed where they cover nothing that matters.
// Usage: scene <image>   → one JSON object on stdout. All boxes are shares of the picture, top-left origin:
//   faces:  every face (x, y, w, h) and its lips box
//   hands:  every hand found (box around its joints)
//   bodies: every person's upper body
//   salient: what draws the eye (attention), as boxes
// macOS Vision only: local, free.
import Foundation
import Vision
import AppKit

func box(_ r: CGRect) -> [String: Double] {
    // Vision is bottom-left origin; flip to top-left
    ["x": Double(r.minX), "y": Double(1 - r.maxY), "w": Double(r.width), "h": Double(r.height)]
}

func pointsBox(_ pts: [CGPoint]) -> [String: Double]? {
    guard !pts.isEmpty else { return nil }
    let xs = pts.map { $0.x }, ys = pts.map { $0.y }
    return box(CGRect(x: xs.min()!, y: ys.min()!, width: xs.max()! - xs.min()!, height: ys.max()! - ys.min()!))
}

let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("{\"error\":\"cannot read image\"}"); exit(1)
}
let faces = VNDetectFaceLandmarksRequest()
let hands = VNDetectHumanHandPoseRequest(); hands.maximumHandCount = 6
let bodies = VNDetectHumanRectanglesRequest(); bodies.upperBodyOnly = true
let attention = VNGenerateAttentionBasedSaliencyImageRequest()
let h = VNImageRequestHandler(cgImage: cg, options: [:])
try? h.perform([faces, hands, bodies, attention])

var out: [String: Any] = [:]
out["faces"] = (faces.results ?? []).map { f -> [String: Any] in
    var row: [String: Any] = ["box": box(f.boundingBox)]
    if let lips = f.landmarks?.outerLips {
        let bb = f.boundingBox
        let pts = lips.normalizedPoints.map { CGPoint(x: bb.minX + $0.x * bb.width, y: bb.minY + $0.y * bb.height) }
        if let b = pointsBox(pts) { row["lips"] = b }
    }
    return row
}
out["hands"] = (hands.results ?? []).compactMap { o -> [String: Double]? in
    guard let pts = try? o.recognizedPoints(.all) else { return nil }
    return pointsBox(pts.values.filter { $0.confidence > 0.3 }.map { $0.location })
}
out["bodies"] = (bodies.results ?? []).map { box($0.boundingBox) }
out["salient"] = ((attention.results?.first as? VNSaliencyImageObservation)?.salientObjects ?? []).map { box($0.boundingBox) }
let data = try! JSONSerialization.data(withJSONObject: out, options: [.sortedKeys])
print(String(data: data, encoding: .utf8)!)
