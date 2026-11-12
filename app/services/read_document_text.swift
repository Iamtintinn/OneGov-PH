import AppKit
import Foundation
import PDFKit
import Vision

func recognize(_ image: CGImage) throws -> String {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["en-US"]
    request.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    try handler.perform([request])
    return (request.results ?? []).compactMap { observation in
        observation.topCandidates(1).first?.string
    }.joined(separator: "\n")
}

func imageFile(_ url: URL) -> CGImage? {
    guard let source = NSImage(contentsOf: url) else { return nil }
    var rect = CGRect(origin: .zero, size: source.size)
    return source.cgImage(forProposedRect: &rect, context: nil, hints: nil)
}

func pdfTextOrImage(_ url: URL) -> CGImage? {
    guard let document = PDFDocument(url: url), let page = document.page(at: 0) else { return nil }
    let extracted = (page.string ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    if extracted.count >= 8 {
        print(extracted)
        exit(0)
    }
    let bounds = page.bounds(for: .mediaBox)
    let scale: CGFloat = 2
    let width = max(Int(bounds.width * scale), 1)
    let height = max(Int(bounds.height * scale), 1)
    guard let context = CGContext(
        data: nil,
        width: width,
        height: height,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else { return nil }
    context.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
    context.fill(CGRect(x: 0, y: 0, width: width, height: height))
    context.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: context)
    return context.makeImage()
}

let arguments = CommandLine.arguments
if arguments.count != 2 {
    fputs("missing file\n", stderr)
    exit(2)
}
let url = URL(fileURLWithPath: arguments[1])
let image: CGImage?
if url.pathExtension.lowercased() == "pdf" {
    image = pdfTextOrImage(url)
} else {
    image = imageFile(url)
}
guard let image else {
    fputs("unreadable\n", stderr)
    exit(2)
}
do {
    print(try recognize(image))
} catch {
    fputs("unreadable\n", stderr)
    exit(2)
}
