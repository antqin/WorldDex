//
//  SignUpView.swift
//  WorldDex
//
//  Created by Anthony Qin on 10/28/23.
//

import SwiftUI

struct SignUpView: View {
    @State private var user_id: String = ""
    @State private var email: String = ""
    @State private var password: String = ""
    @Binding var isLoggedIn: Bool
    @Binding var username: String
    
    let signUpUrl = URL(string: Constants.baseURL + Constants.Endpoints.register)!

    var body: some View {
        ZStack {
            // Custom background color. Replace with your desired background.
            Color("theme1").edgesIgnoringSafeArea(.all)
            VStack(spacing: 20) {
                Image("logo")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 100, height: 100)
                    .padding()
                TextField("Username", text: $user_id)
                    .font(Font.custom("Avenir", size: 16))
                    .padding(10)
                    .background(Color("theme2"))
                    .cornerRadius(5)
                    .overlay(
                        RoundedRectangle(cornerRadius: 5)
                            .stroke(Color.gray, lineWidth: 1)
                    )
                TextField("Email", text: $email)
                    .font(Font.custom("Avenir", size: 16))
                    .padding(10)
                    .background(Color("theme2"))
                    .cornerRadius(5)
                    .overlay(
                        RoundedRectangle(cornerRadius: 5)
                            .stroke(Color.gray, lineWidth: 1)
                    )
                SecureField("Password", text: $password)
                    .font(Font.custom("Avenir", size: 16))
                    .padding(10)
                    .background(Color("theme2"))
                    .cornerRadius(5)
                    .overlay(
                        RoundedRectangle(cornerRadius: 5)
                            .stroke(Color.gray, lineWidth: 1)
                    )
                
                Button(action: signUp) {
                    Text("Sign Up")
                        .font(Font.custom("Avenir", size: 20))
                        .padding(10)
                        .background(Color("theme2"))
                        .foregroundColor(Color("theme1"))
                        .cornerRadius(5)
                }
            }
            .padding()
        }
    }

    func signUp() {
        // Encode the parameters in the query string
        let queryItems = [
            URLQueryItem(name: "username", value: user_id),
            URLQueryItem(name: "password", value: password),
            URLQueryItem(name: "ethereum_address", value: ""), // Example value
            URLQueryItem(name: "email", value: email)
        ]
        var urlComponents = URLComponents(string: Constants.baseURL + Constants.Endpoints.register)!
        urlComponents.queryItems = queryItems

        guard let signUpUrl = urlComponents.url else {
            print("Invalid URL")
            return
        }

        var request = URLRequest(url: signUpUrl)
        request.httpMethod = "POST"
        
        // No need to set a JSON body or content-type header for query parameters
        URLSession.shared.dataTask(with: request) { (data, response, error) in
            // Handle response here
            if let error = error {
                print("Error: \(error)")
            } else if let httpResponse = response as? HTTPURLResponse {
                if httpResponse.statusCode == 200 {
                    DispatchQueue.main.async {
                        self.isLoggedIn = true
                        self.username = user_id
                        UserDefaults.standard.set(true, forKey: "isLoggedIn")
                        UserDefaults.standard.set(user_id, forKey: "username")
                    }
                } else {
                    // Handle other status codes or show an error message
                    print("Error: HTTP Status Code \(httpResponse.statusCode)")
                }
            }
        }.resume()
    }
}

