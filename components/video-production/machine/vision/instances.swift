// instances.swift — cut every separate foreground object out of an image (macOS Vision).
// usage: instances <in.png> <outdir>   → <outdir>/inst-<n>.png masks at image size, one per object
import Foundation
import Vision
import AppKit
import CoreImage
let a = CommandLine.arguments
guard let img = NSImage(contentsOf: URL(fileURLWithPath: a[1])),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(2) }
let req = VNGenerateForegroundInstanceMaskRequest()
let h = VNImageRequestHandler(cgImage: cg, options: [:])
try? h.perform([req])
guard let r = req.results?.first else { print("none"); exit(3) }
let ctx = CIContext()
for i in r.allInstances {
    guard let buf = try? r.generateScaledMaskForImage(forInstances: IndexSet(integer: i), from: h) else { continue }
    let ci = CIImage(cvPixelBuffer: buf)
    if let out = ctx.createCGImage(ci, from: ci.extent) {
        let rep = NSBitmapImageRep(cgImage: out)
        try? rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "\(a[2])/inst-\(i).png"))
        print("inst-\(i)")
    }
}
