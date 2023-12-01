//
//  LogInView.swift
//  WorldDex
//
//  Created by Anthony Qin on 10/28/23.
//

import SwiftUI

struct LogInView: View {
    @State private var user_id: String = ""
    @State private var password: String = ""
    @State private var showUserData = false
    @State private var showError = false
    @Binding var isLoggedIn: Bool
    @Binding var username: String
    
    let loginUrl = URL(string: Constants.baseURL + Constants.Endpoints.login)!


    var body: some View {
        ZStack {
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
                SecureField("Password", text: $password)
                    .font(Font.custom("Avenir", size: 16))
                    .padding(10)
                    .background(Color("theme2"))
                    .cornerRadius(5)
                    .overlay(
                        RoundedRectangle(cornerRadius: 5)
                            .stroke(Color.gray, lineWidth: 1)
                    )
                if showError {
                    Text("Incorrect credentials!")
                        .foregroundColor(.red)
                }
                Button(action: logIn) {
                    Text("Log In")
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

    func logIn() {
        var request = URLRequest(url: loginUrl)
            request.httpMethod = "POST"

            // Prepare form data
            let formData = "username=\(user_id)&password=\(password)"
            request.httpBody = formData.data(using: .utf8)
            
            // Set the content type to application/x-www-form-urlencoded
            request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")

            URLSession.shared.dataTask(with: request) { data, response, error in
                if let httpResponse = response as? HTTPURLResponse {
                    switch httpResponse.statusCode {
                    case 200:
                        print("SUCCESSFUL LOGIN")
                        DispatchQueue.main.async {
                            self.isLoggedIn = true
                            self.username = user_id
                            UserDefaults.standard.set(true, forKey: "isLoggedIn")
                            UserDefaults.standard.set(user_id, forKey: "username")
                            self.showError = false
                        }
                    case 401:
                        print("FAIL LOGIN: Invalid username or password")
                        DispatchQueue.main.async {
                            self.showError = true
                        }
                    default:
                        print("FAIL LOGIN: Server error")
                        DispatchQueue.main.async {
                            self.showError = true
                        }
                    }
                } else if let error = error {
                    print("Error fetching data: \(error)")
                }
            }.resume()
    }
}


