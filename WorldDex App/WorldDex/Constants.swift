//
//  Constants.swift
//  WorldDex
//
//  Created by Jaiden Reddy on 11/30/23.
//

struct Constants {
    static let baseURL = "http://52.249.222.215:8000"
    static let inferenceURL = "http://104.42.251.202:5000"
    static let conversationURL = "http://104.42.251.202:5001"
    struct Endpoints {
        static let register = "/registerUser"
        static let login = "/login"
        static let usernames = "/getAllUsernames"
        static let image = "/getSpecificImage"
        static let userImages = "/getUserImageUrls"
        static let excludeUserImages = "/excludeUserImageUrls"
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
