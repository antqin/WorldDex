//
//  PokemonDetailView.swift
//  WorldDex
//
//  Created by Anthony Qin on 10/27/23.
//

import SwiftUI
import Speech
import AVFoundation
import Kingfisher

class AudioPlayerDelegate: NSObject, AVAudioPlayerDelegate {
    var stopPlayingCallback: (() -> Void)?

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        stopPlayingCallback?()
    }
}

struct PokemonDetailView: View {
    var pokemon: Pokemon
    @State private var isPressed = false
    @State private var audioEngine = AVAudioEngine()
    @State private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    @State private var recognitionTask: SFSpeechRecognitionTask?
    @State private var speechRecognizer = SFSpeechRecognizer()
    @State private var finalTranscription: String?
    
    // Audio Playback
    @State private var isLoading: Bool = false // Track loading state for audio
    @State private var audioPlayer: AVAudioPlayer?
    @State private var isPlaying = false
    
    @State private var isFlashing = false
    @State private var audioLevelTimer: Timer?
    @State private var audioPlayerDelegate = AudioPlayerDelegate()
    
    var formattedDate: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSZ"
        if let date = formatter.date(from: pokemon.date_added) {
            formatter.dateFormat = "MM/dd/yyyy hh:mm:ss a"
            return formatter.string(from: date)
        }
        return pokemon.date_added
    }
    
    var captureText: String {
        let chance = String(pokemon.probability.prefix(4))
        let item = pokemon.image_classification.split(separator: "_").first ?? ""
        return "You had a \(chance)% chance of capturing this \(item)!"
    }

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                Color("theme1").edgesIgnoringSafeArea(.all)

                VStack(spacing: 10) {
                    // Use Kingfisher to load the image from the URL
                    KFImage(URL(string: pokemon.image_url))
                        .resizable()
                        .scaledToFit()
                        .frame(width: 250, height: 300)
                    
                    Text(pokemon.image_classification.split(separator: "_").first ?? "")
                        .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .largeTitle).pointSize))
                        .foregroundColor(.black)
                        .bold()
                    
                    VStack(alignment: .leading) {
                        HStack {
                            Text(pokemon.location_taken)
                                .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .subheadline).pointSize))
                            Text(formattedDate)
                                .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .subheadline).pointSize))
                        }
                        Text(captureText)
                            .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .subheadline).pointSize))
                            .italic()
                            .lineLimit(nil)
                            .fixedSize(horizontal: false, vertical: true)
                            .multilineTextAlignment(.leading)
                            .foregroundColor(.black)
                    }
                    .foregroundColor(.black)
                    Spacer()
                    VStack(alignment: .leading, spacing: 0) {
                        Text("Live Observations:")
                            .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .title3).pointSize))
                            .bold()
                        ScrollView {
                            Text(pokemon.details)
                                .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .subheadline).pointSize))
                                .lineLimit(nil)
                                .fixedSize(horizontal: false, vertical: true)
                                .multilineTextAlignment(.leading)
                        }
                    }
                    .foregroundColor(.black)
                    
                    if isLoading {
                        GifImageView(gifName: "loading", desiredWidth: 50, desiredHeight: 50)
                            .frame(width: 50, height: 50)
                    } else {
                        if isPlaying {
                            Circle()
                                .fill(isFlashing ? Color.orange : Color.gray)
                                .frame(width: 50, height: 50)
                                .animation(.default)
                                .onAppear {
                                    audioPlayerDelegate.stopPlayingCallback = {
                                        stopPlaying()
                                    }
                                }
                        } else {
                            Button(action: {}, label: {
                                Image(systemName: "mic.fill")
                                    .resizable()
                                    .frame(width: 40, height: 60)
                                    .colorMultiply(isPressed ? Color.gray : Color.white) // Highlight effect
                                    .onLongPressGesture(minimumDuration: .infinity, pressing: { isPressing in
                                        self.isPressed = isPressing
                                        if isPressing {
                                            DispatchQueue.main.async {
                                                // Haptic feedback
                                                let generator = UIImpactFeedbackGenerator(style: .medium)
                                                generator.impactOccurred()
                                            }
                                            startRecording()
                                        } else {
                                            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                                                stopRecording()
                                                isLoading = true
                                            }
                                        }
                                    }, perform: {})
                            })
                            Text("Press and hold to talk to AI")
                                .font(Font.custom("Avenir", size: 20))
                                .foregroundColor(Color("theme2"))
                                .padding(.bottom, 10)
                        }
                    }
                }
                .offset(y: -geometry.size.height * 0.05)
            }
        }
    }
    
    func startPlaying() {
        audioPlayer?.play()
        isLoading = false
        isPlaying = true
        
        audioLevelTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true, block: { _ in
            guard let player = audioPlayer else {
                return
            }
            // This is a mock condition, you can replace with an actual check for audio level
            self.isFlashing = player.isPlaying && Int.random(in: 0...3) == 0
        })
    }
    
    func stopPlaying() {
        isPlaying = false
        isFlashing = false
        audioPlayer?.stop()
        audioLevelTimer?.invalidate()
    }

    func pokemonImage(from base64: String) -> UIImage {
        guard let data = Data(base64Encoded: base64), let image = UIImage(data: data) else {
            return UIImage() // or a default image if desired
        }
        return image
    }
    
    func startRecording() {
        do {
            // 1. Resetting any existing recognitionRequest and recognitionTask
            recognitionTask?.cancel()
            recognitionTask = nil
            
            recognitionRequest = nil
            recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
            
            let inputNode = audioEngine.inputNode
            
            // Remove existing tap if there is one
            inputNode.removeTap(onBus: 0) // <-- Add this line to ensure only one tap is active
            
            guard let recognitionRequest = recognitionRequest else { fatalError("Unable to create request object") }
            recognitionRequest.shouldReportPartialResults = true
            
            recognitionTask = speechRecognizer?.recognitionTask(with: recognitionRequest) { result, error in
                if let result = result {
                    print(result.bestTranscription.formattedString)
                    finalTranscription = result.bestTranscription.formattedString
                }
            }
            
            let recordingFormat = inputNode.outputFormat(forBus: 0)
            inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { (buffer, _) in
                recognitionRequest.append(buffer)
            }
            
            if !audioEngine.isRunning { // <-- Check if the engine isn't already running
                audioEngine.prepare()
                try audioEngine.start()
            }
        } catch {
            print("There was an error starting the audio engine")
        }
    }

    func stopRecording() {
        if audioEngine.isRunning {
            isLoading = true
            audioEngine.stop()
            recognitionRequest?.endAudio()
            recognitionTask?.cancel()
            recognitionTask = nil
            
            if let transcription = finalTranscription {
                sendTranscriptionToServer(transcription: transcription)
            }
        }
    }
    
    func sendTranscriptionToServer(transcription: String) {
        guard let url = URL(string: Constants.conversationURL + Constants.responseEndpoints.respond) else {
            print("Invalid URL")
            return
        }
        
        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpMethod = "POST"
        
        let requestBody = [
            "text": transcription,
            "image_name": pokemon.image_classification.split(separator: "_").first ?? ""
        ] as [String : Any]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        } catch {
            print("Failed to serialize data to JSON")
            return
        }
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                print("Error sending data: \(error)")
                return
            }
            
            if let data = data {
                DispatchQueue.main.async {
                    self.audioPlayer = try? AVAudioPlayer(data: data)
                    self.audioPlayer?.delegate = self.audioPlayerDelegate  // <-- Use the new delegate instance
                    self.audioPlayer?.prepareToPlay()
                    self.startPlaying()
                }
            } else {
                print("Received no data in response")
            }
        }.resume()
    }

}

