//
//  SuccessView.swift
//  WorldDex
//
//  Created by Anthony Qin on 10/28/23.
//

import SwiftUI
import AVFoundation
import Speech

#if canImport(UIKit)
extension View {
    func endEditing() {
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }
}
#endif

struct SuccessView: View {
    var item: String
    var originalImage: UIImage?
    var croppedImage: UIImage?
    var location: String
    var timestamp: String
    var probability: Float
    var userId: String = UserDefaults.standard.string(forKey: "username") ?? ""
    @State var recordingText: String = ""
    var callback: (() -> Void)?

    // Speech recognition properties
    @State private var isRecording = false
    private let speechRecognizer = SFSpeechRecognizer()
    private let audioEngine = AVAudioEngine()
    @State private var lastTranscriptionTime = Date()
    @State private var isTextFieldActive = false
    
    let uploadUrl = URL(string: Constants.baseURL + Constants.Endpoints.upload)!

    var body: some View {
        ZStack {
            Color("theme1").edgesIgnoringSafeArea(.all)
            VStack(spacing: 20) {
                if !isTextFieldActive {
                    Text("Congrats! You have captured \(item).")
                        .font(Font.custom("Avenir", size: 34))
                        .foregroundColor(Color.black)
                        .padding([.top, .leading, .trailing])
                    
                    Image(uiImage: croppedImage ?? UIImage())
                        .resizable()
                        .scaledToFit()
                        .frame(width: 200, height: 200)
                    Text("You had a \(String(format: "%.1f", probability))% chance of capturing it!")
                        .font(Font.custom("Avenir", size: 16))
                        .foregroundColor(Color.black)
                    HStack {
                        Text(location)
                            .foregroundColor(Color.black)
                            .font(Font.custom("Avenir", size: 22))
                        Spacer()
                        Text(timestamp)
                            .font(Font.custom("Avenir", size: 22))
                            .foregroundColor(Color.black)
                    }
                    .padding([.leading, .trailing])
                    
                    // Only show the mic button when not editing text
                    if recordingText.isEmpty {
                        Text("Press to record live voice transcription notes")
                            .font(Font.custom("Avenir", size: 20))
                            .foregroundColor(Color("theme2"))
                        Button(action: startRecording) {
                            Image(systemName: "mic.fill")
                                .resizable()
                                .frame(width: 50, height: 80)
                        }
                    }
                }
                
                if isTextFieldActive || !recordingText.isEmpty {
                    ScrollView {
                        UITextViewWrapper(text: $recordingText)
                            .frame(minHeight: 200)
                            .padding()
                            .onTapGesture {
                                self.isTextFieldActive = true
                            }
                    }
                }
                
                Button("Done") {
                    stopRecording()
                    self.isTextFieldActive = false
                    callback?()

                    let croppedImageData: Data? = croppedImage?.jpegData(compressionQuality: 0.5)
                    let croppedImageBase64String: String? = croppedImageData?.base64EncodedString()
                    let originalImageData: Data? = originalImage?.jpegData(compressionQuality: 0.5)
                    let originalImageBase64String: String? = originalImageData?.base64EncodedString()

                    let uploadUrl = URL(string: Constants.baseURL + Constants.Endpoints.upload)!
                    var request = URLRequest(url: uploadUrl)
                    request.httpMethod = "POST"

                    // Prepare form data
                    var components = URLComponents()
                    components.queryItems = [
                        URLQueryItem(name: "image_base64", value: originalImageBase64String),
                        URLQueryItem(name: "cropped_image_base64", value: croppedImageBase64String),
                        URLQueryItem(name: "user_id", value: userId),
                        URLQueryItem(name: "location_taken", value: location),
                        URLQueryItem(name: "details", value: recordingText),
                        URLQueryItem(name: "probability", value: String(probability)),
                        URLQueryItem(name: "image_classification", value: item)  // Assuming 'item' is your image classification
                    ]

                    // Note: Add other fields like 'decentralize_storage', 'eth_address' if necessary
                    // ...

                    request.httpBody = components.query?.data(using: .utf8)
                    request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")

                    URLSession.shared.dataTask(with: request) { (data, response, error) in
                        // Handle response here
                        if let httpResponse = response as? HTTPURLResponse {
                            if httpResponse.statusCode == 201 {
                                print("Upload successful")
                            } else {
                                print("Upload failed with status: \(httpResponse.statusCode)")
                            }
                        } else if let error = error {
                            print("Error: \(error)")
                        }
                    }.resume()
                }
                .font(Font.custom("Avenir", size: 20))
                .padding(10)
                .background(Color("theme2"))
                .foregroundColor(Color("theme1"))
                .cornerRadius(5)
            }
            .onTapGesture {
                self.endEditing()
                self.isTextFieldActive = false
            }
        }
    }
    
    func startRecording() {
        lastTranscriptionTime = Date()
        isRecording = true
        let recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        let inputNode = audioEngine.inputNode
        recordingText = "Start speaking!"
        
        guard let recognitionTask = try? speechRecognizer?.recognitionTask(with: recognitionRequest, resultHandler: { (result, error) in
            if let result = result {
                if Date().timeIntervalSince(self.lastTranscriptionTime) >= 3.0 {
                    print("STOP RECORDING")
                    self.stopRecording()
                } else {
                    self.recordingText = result.bestTranscription.formattedString
                    print(self.recordingText)
                    self.lastTranscriptionTime = Date()
                }
            }
        }) else { return }
        
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { (buffer, time) in
            recognitionRequest.append(buffer)
        }
        
        audioEngine.prepare()
        try? audioEngine.start()
    }
    
    func stopRecording() {
        if !isRecording { return }
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        isRecording = false
    }
    
    func requestSpeechAuthorization() {
        SFSpeechRecognizer.requestAuthorization { authStatus in
            // Handle authorization status here. For simplicity, we're just printing it.
            print(authStatus)
        }
    }
}

