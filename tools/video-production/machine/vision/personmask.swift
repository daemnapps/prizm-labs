// personmask.swift — write a white-on-black mask of every person in an image
// (bodies, arms, hands) at the image's own size. macOS Vision, nothing to install.
// usage: personmask <in.png> <out-mask.png>
import Foundation
import Vision
import AppKit
import CoreImage
let a = CommandLine.arguments
guard let img = NSImage(contentsOf: URL(fileURLWithPath: a[1])),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(2) }
let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8
try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
guard let buf = req.results?.first?.pixelBuffer else { exit(3) }
var mask = CIImage(cvPixelBuffer: buf)
let sx = CGFloat(cg.width) / mask.extent.width, sy = CGFloat(cg.height) / mask.extent.height
mask = mask.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
let ctx = CIContext()
guard let out = ctx.createCGImage(mask, from: CGRect(x: 0, y: 0, width: cg.width, height: cg.height)) else { exit(4) }
let rep = NSBitmapImageRep(cgImage: out)
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: a[2]))
