//
//  UserDataView.swift
//  WorldDex
//
//  Created by Anthony Qin on 10/28/23.
//

import SwiftUI

struct UserDataView: View {
    var username: String
    @Binding var isLoggedIn: Bool
    @State private var email: String = ""
    
    let userDataUrl = URL(string: Constants.baseURL + Constants.Endpoints.userData)!
    
    var body: some View {
        ZStack {
            Color("theme1").edgesIgnoringSafeArea(.all)
            VStack(spacing: 20) {
                Image("logo")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 100, height: 100)
                    .padding()
                Text("Username: \(username)")
                    .font(Font.custom("Avenir", size: 20))
                    .foregroundColor(Color("theme2"))
                Text("Email: \(email)")
                    .font(Font.custom("Avenir", size: 20))
                    .foregroundColor(Color("theme2"))
                Button("Logout") {
                    logOut()
                }
                .font(Font.custom("Avenir", size: 20))
                .padding(10)
                .background(Color("theme2"))
                .foregroundColor(Color("theme1"))
                .cornerRadius(5)
            }
            .padding()
            .onAppear {
                fetchUserData()
            }
        }
    }
    
    func fetchUserData() {
        let userDataUrl = URL(string: Constants.baseURL + Constants.Endpoints.userData + "?username=\(username)")!

        URLSession.shared.dataTask(with: userDataUrl) { data, response, error in
            guard let data = data else {
                print("Error fetching data: \(String(describing: error))")
                return
            }

            do {
                if let jsonResponse = try JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] {
                    DispatchQueue.main.async {
                        if let userEmail = jsonResponse["email"] as? String {
                            self.email = userEmail
                        }
                        // NOTE: insert a property to store ethereum address
                    }
                }
            } catch {
                print("Error decoding: \(error)")
            }
        }.resume()
    }

    
    func logOut() {
        UserDefaults.standard.set(false, forKey: "isLoggedIn")
        UserDefaults.standard.set("", forKey: "username")
        isLoggedIn = false
    }
}


