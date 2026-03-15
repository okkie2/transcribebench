import AVFAudio
import Foundation
import Speech

struct JSONPrinter {
    static func printObject(_ object: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: object, options: []),
              let text = String(data: data, encoding: .utf8) else {
            Swift.print("{\"error\":\"Failed to encode JSON output\"}")
            return
        }
        Swift.print(text)
    }
}

enum CommandMode {
    case transcribe
    case checkAssets
    case installAssets
    case listLocales
    case dictation
}

enum AppleSpeechError: Error, CustomStringConvertible {
    case invalidArguments(String)
    case unsupportedPlatform
    case unsupportedLocale(String)
    case missingAssets(String)
    case emptyTranscript

    var description: String {
        switch self {
        case .invalidArguments(let message):
            return message
        case .unsupportedPlatform:
            return "Apple Speech requires macOS 26 or newer."
        case .unsupportedLocale(let locale):
            return "SpeechTranscriber does not support locale \(locale) on this machine."
        case .missingAssets(let locale):
            return "Speech assets for locale \(locale) are not installed on this machine."
        case .emptyTranscript:
            return "SpeechTranscriber returned an empty transcript."
        }
    }
}

@available(macOS 26.0, *)
func collectTranscript(from transcriber: SpeechTranscriber) async throws -> String {
    var latestFinalText = ""
    var latestObservedText = ""

    for try await result in transcriber.results {
        let text = String(result.text.characters).trimmingCharacters(in: .whitespacesAndNewlines)
        if !text.isEmpty {
            latestObservedText = text
        }
        if result.isFinal && !text.isEmpty {
            latestFinalText = text
        }
    }

    let transcript = latestFinalText.isEmpty ? latestObservedText : latestFinalText
    if transcript.isEmpty {
        throw AppleSpeechError.emptyTranscript
    }
    return transcript
}

@available(macOS 26.0, *)
func collectTranscript(from transcriber: DictationTranscriber) async throws -> String {
    var latestFinalText = ""
    var latestObservedText = ""

    for try await result in transcriber.results {
        let text = String(result.text.characters).trimmingCharacters(in: .whitespacesAndNewlines)
        if !text.isEmpty {
            latestObservedText = text
        }
        if result.isFinal && !text.isEmpty {
            latestFinalText = text
        }
    }

    let transcript = latestFinalText.isEmpty ? latestObservedText : latestFinalText
    if transcript.isEmpty {
        throw AppleSpeechError.emptyTranscript
    }
    return transcript
}

func parseArgs() throws -> (audio: String?, locale: String, mode: CommandMode, useDictationModuleForAssets: Bool) {
    var audio: String?
    var locale: String?
    var mode: CommandMode = .transcribe
    var useDictationModuleForAssets = false

    var index = 1
    let args = CommandLine.arguments
    while index < args.count {
        let arg = args[index]
        switch arg {
        case "--audio":
            index += 1
            if index < args.count {
                audio = args[index]
            }
        case "--locale":
            index += 1
            if index < args.count {
                locale = args[index]
            }
        case "--check-assets":
            mode = .checkAssets
        case "--install-assets":
            mode = .installAssets
        case "--list-locales":
            mode = .listLocales
        case "--dictation":
            mode = .dictation
        case "--use-dictation-module":
            useDictationModuleForAssets = true
        default:
            break
        }
        index += 1
    }

    guard mode == .listLocales || locale != nil else {
        throw AppleSpeechError.invalidArguments("Usage: apple-speech-cli [--audio <path>] --locale <locale> [--check-assets|--install-assets]")
    }
    if (mode == .transcribe || mode == .dictation) && audio == nil {
        throw AppleSpeechError.invalidArguments("Usage: apple-speech-cli --audio <path> --locale <locale>")
    }
    return (audio: audio, locale: locale ?? "", mode: mode, useDictationModuleForAssets: useDictationModuleForAssets)
}

@available(macOS 26.0, *)
func transcriberForLocale(_ localeIdentifier: String) async throws -> (Locale, SpeechTranscriber) {
    let requestedLocale = Locale(identifier: localeIdentifier)
    guard let matchedLocale = await SpeechTranscriber.supportedLocale(equivalentTo: requestedLocale) else {
        throw AppleSpeechError.unsupportedLocale(localeIdentifier)
    }
    return (matchedLocale, SpeechTranscriber(locale: matchedLocale, preset: .transcription))
}

@available(macOS 26.0, *)
func dictationTranscriberForLocale(_ localeIdentifier: String) async throws -> (Locale, DictationTranscriber) {
    let requestedLocale = Locale(identifier: localeIdentifier)
    guard let matchedLocale = await DictationTranscriber.supportedLocale(equivalentTo: requestedLocale) else {
        throw AppleSpeechError.unsupportedLocale(localeIdentifier)
    }
    return (matchedLocale, DictationTranscriber(locale: matchedLocale, preset: .longDictation))
}

func stringStatus(_ status: AssetInventory.Status) -> String {
    switch status {
    case .installed:
        return "installed"
    case .downloading:
        return "installing"
    case .supported:
        return "missing"
    case .unsupported:
        return "unsupported"
    default:
        return "unknown"
    }
}

@main
struct AppleSpeechCLI {
    static func main() async {
        do {
            let parsed = try parseArgs()

            guard #available(macOS 26.0, *) else {
                throw AppleSpeechError.unsupportedPlatform
            }

            if parsed.mode == .listLocales {
                let locales = await SpeechTranscriber.supportedLocales.map(\.identifier).sorted()
                let installed = await SpeechTranscriber.installedLocales.map(\.identifier).sorted()
                let dictationLocales = await DictationTranscriber.supportedLocales.map(\.identifier).sorted()
                let dictationInstalled = await DictationTranscriber.installedLocales.map(\.identifier).sorted()
                JSONPrinter.printObject([
                    "supported_locales": locales,
                    "installed_locales": installed,
                    "dictation_supported_locales": dictationLocales,
                    "dictation_installed_locales": dictationInstalled,
                ])
                return
            }

            switch parsed.mode {
            case .listLocales:
                JSONPrinter.printObject([
                    "supported_locales": [],
                    "installed_locales": [],
                ])
            case .checkAssets:
                if parsed.useDictationModuleForAssets {
                    let (matchedLocale, transcriber) = try await dictationTranscriberForLocale(parsed.locale)
                    let assetStatus = await AssetInventory.status(forModules: [transcriber])
                    JSONPrinter.printObject([
                        "status": stringStatus(assetStatus),
                        "locale": matchedLocale.identifier,
                        "module": "dictation",
                    ])
                    return
                }
                let (matchedLocale, transcriber) = try await transcriberForLocale(parsed.locale)
                let assetStatus = await AssetInventory.status(forModules: [transcriber])
                JSONPrinter.printObject([
                    "status": stringStatus(assetStatus),
                    "locale": matchedLocale.identifier,
                ])
            case .installAssets:
                if parsed.useDictationModuleForAssets {
                    let (matchedLocale, transcriber) = try await dictationTranscriberForLocale(parsed.locale)
                    let assetStatus = await AssetInventory.status(forModules: [transcriber])
                    if assetStatus == .installed {
                        JSONPrinter.printObject([
                            "status": "installed",
                            "locale": matchedLocale.identifier,
                            "module": "dictation",
                        ])
                        return
                    }
                    guard let request = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) else {
                        JSONPrinter.printObject([
                            "status": stringStatus(assetStatus),
                            "locale": matchedLocale.identifier,
                            "module": "dictation",
                            "error": "No install request available for locale \(matchedLocale.identifier).",
                        ])
                        return
                    }
                    try await request.downloadAndInstall()
                    let updatedStatus = await AssetInventory.status(forModules: [transcriber])
                    JSONPrinter.printObject([
                        "status": stringStatus(updatedStatus),
                        "locale": matchedLocale.identifier,
                        "module": "dictation",
                    ])
                    return
                }
                let (matchedLocale, transcriber) = try await transcriberForLocale(parsed.locale)
                let assetStatus = await AssetInventory.status(forModules: [transcriber])
                if assetStatus == .installed {
                    JSONPrinter.printObject([
                        "status": "installed",
                        "locale": matchedLocale.identifier,
                    ])
                    return
                }
                guard let request = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) else {
                    JSONPrinter.printObject([
                        "status": stringStatus(assetStatus),
                        "locale": matchedLocale.identifier,
                        "error": "No install request available for locale \(matchedLocale.identifier).",
                    ])
                    return
                }
                try await request.downloadAndInstall()
                let updatedStatus = await AssetInventory.status(forModules: [transcriber])
                JSONPrinter.printObject([
                    "status": stringStatus(updatedStatus),
                    "locale": matchedLocale.identifier,
                ])
            case .transcribe:
                let (matchedLocale, transcriber) = try await transcriberForLocale(parsed.locale)
                let assetStatus = await AssetInventory.status(forModules: [transcriber])
                guard assetStatus == .installed else {
                    throw AppleSpeechError.missingAssets(matchedLocale.identifier)
                }
                guard let audioPath = parsed.audio else {
                    throw AppleSpeechError.invalidArguments("Usage: apple-speech-cli --audio <path> --locale <locale>")
                }

                let audioURL = URL(fileURLWithPath: audioPath)
                let audioFile = try AVAudioFile(forReading: audioURL)
                let analyzer = SpeechAnalyzer(modules: [transcriber])

                async let transcriptTask = collectTranscript(from: transcriber)
                try await analyzer.start(inputAudioFile: audioFile, finishAfterFile: true)
                let transcript = try await transcriptTask

                JSONPrinter.printObject(["text": transcript])
            case .dictation:
                let (matchedLocale, transcriber) = try await dictationTranscriberForLocale(parsed.locale)
                let assetStatus = await AssetInventory.status(forModules: [transcriber])
                guard assetStatus == .installed else {
                    throw AppleSpeechError.missingAssets(matchedLocale.identifier)
                }
                guard let audioPath = parsed.audio else {
                    throw AppleSpeechError.invalidArguments("Usage: apple-speech-cli --dictation --audio <path> --locale <locale>")
                }

                let audioURL = URL(fileURLWithPath: audioPath)
                let audioFile = try AVAudioFile(forReading: audioURL)
                let analyzer = SpeechAnalyzer(modules: [transcriber])

                async let transcriptTask = collectTranscript(from: transcriber)
                try await analyzer.start(inputAudioFile: audioFile, finishAfterFile: true)
                let transcript = try await transcriptTask

                JSONPrinter.printObject(["text": transcript])
            }
        } catch {
            JSONPrinter.printObject(["error": String(describing: error)])
            Foundation.exit(0)
        }
    }
}
