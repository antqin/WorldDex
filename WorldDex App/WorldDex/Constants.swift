//
//  Constants.swift
//  WorldDex
//
//  Created by Jaiden Reddy on 11/30/23.
//

struct Constants {
    static let baseURL = "https://worlddex.ngrok.app"
    static let inferenceURL = "http://104.42.251.202:5000"
    static let respondURL = ""
    struct Endpoints {
        static let register = "/registerUser"
        static let login = "/login"
        static let usernames = "/getAllUsernames"
        static let image = "/getSpecificImage"
        static let userImages = "/getUserImages"
        static let excludeUserImages = "/excludeUserImages"
        static let upload = "/upload"
        static let userData = "/userData"
    }
    struct inferenceEndpoints {
        static let predict = "/predict"
    }
    struct responseEndpoints {
        static let respond = "/respond"
    }
}
