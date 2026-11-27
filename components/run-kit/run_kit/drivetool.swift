import Foundation
// drivetool status <path>...  -> per file: "<uploaded 0|1>\t<path>" (folders are walked)
// drivetool evict  <path>...  -> drops this Mac's copy of each UPLOADED file; it stays in Drive
//                                 and comes back when something opens it. Never deletes.
// Built and cached by run_kit/drive_hand.py on first use (swiftc); never committed as a binary.
let args = CommandLine.arguments
guard args.count >= 3, args[1] == "status" || args[1] == "evict" else {
    print("usage: drivetool status|evict <path>..."); exit(2)
}
let mode = args[1]
let fm = FileManager.default
let keys: [URLResourceKey] = [.isRegularFileKey, .ubiquitousItemIsUploadedKey]

func each(_ root: URL, _ f: (URL) -> Void) {
    var isDir: ObjCBool = false
    guard fm.fileExists(atPath: root.path, isDirectory: &isDir) else { return }
    if !isDir.boolValue { f(root); return }
    if let e = fm.enumerator(at: root, includingPropertiesForKeys: keys, options: []) {
        for case let u as URL in e { f(u) }
    }
}

for p in args[2...] {
    each(URL(fileURLWithPath: p).resolvingSymlinksInPath()) { u in
        guard let v = try? u.resourceValues(forKeys: Set(keys)), v.isRegularFile == true else { return }
        let up = v.ubiquitousItemIsUploaded ?? false
        if mode == "status" { print("\(up ? 1 : 0)\t\(u.path)"); return }
        if !up { print("held\t\(u.path)"); return }
        do { try fm.evictUbiquitousItem(at: u); print("dropped\t\(u.path)") }
        catch { print("failed\t\(u.path)\t\(error.localizedDescription)") }
    }
}
