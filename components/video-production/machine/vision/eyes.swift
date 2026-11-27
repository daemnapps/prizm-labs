// eyes.swift — for every image in a folder (sorted): the largest face's box and both pupils
// "<file> fx fy fw fh lx ly rx ry" (0..1 of the image, top-left origin; -1 when not found).
// Used by face_lock.py to measure eye colour against the casting sheet (2026-10-03).
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
        print("\(u.lastPathComponent) -1 -1 -1 -1 -1 -1 -1 -1"); continue }
    let b = f.boundingBox
    func pt(_ r: VNFaceLandmarkRegion2D?) -> (Double, Double) {
        guard let p = r?.normalizedPoints.first else { return (-1, -1) }
        return (Double(b.minX + CGFloat(p.x) * b.width), Double(1 - (b.minY + CGFloat(p.y) * b.height)))
    }
    let l = pt(f.landmarks?.leftPupil), r = pt(f.landmarks?.rightPupil)
    print(String(format: "%@ %.4f %.4f %.4f %.4f %.4f %.4f %.4f %.4f", u.lastPathComponent, b.minX, 1 - b.maxY, b.width, b.height, l.0, l.1, r.0, r.1))
}
