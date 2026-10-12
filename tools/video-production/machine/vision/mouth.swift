// mouth.swift — for every image in a folder (sorted), the largest face and how open
// its mouth is: "<file> fx fy fw fh open" (0..1, top-left origin; open = inner-lip
// height / inner-lip width, -1 when no face). macOS Vision, no install. Used by
// clip_qc.py to check lip sync, zoom and camera movement frame by frame (2026-10-02).
import Foundation
import Vision
import AppKit
let dir = URL(fileURLWithPath: CommandLine.arguments[1])
let files = (try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)) ?? []
for u in files.filter({ ["jpg", "png"].contains($0.pathExtension.lowercased()) }).sorted(by: { $0.lastPathComponent < $1.lastPathComponent }) {
    guard let img = NSImage(contentsOf: u), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let req = VNDetectFaceLandmarksRequest()
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    guard let f = (req.results ?? []).max(by: { $0.boundingBox.width < $1.boundingBox.width }) else {
        print("\(u.lastPathComponent) 0 0 0 0 -1"); continue }
    var open = -1.0
    if let lips = f.landmarks?.innerLips?.normalizedPoints, lips.count > 2 {
        let xs = lips.map { Double($0.x) }, ys = lips.map { Double($0.y) }
        let w = (xs.max()! - xs.min()!), h = (ys.max()! - ys.min()!)
        open = w > 0 ? h / w : -1
    }
    let b = f.boundingBox
    print(String(format: "%@ %.4f %.4f %.4f %.4f %.4f", u.lastPathComponent, b.minX, 1 - b.maxY, b.width, b.height, open))
}
