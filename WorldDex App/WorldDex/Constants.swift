//
//  Constants.swift
//  WorldDex
//
//  Created by Jaiden Reddy on 11/30/23.
//

struct Constants {
    static let baseURL = "http://10.31.68.30:8000"
    static let inferenceURL = "http://54.69.7.221:5001"
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
        static let respond = "/respond"
        static let predict = "/predict"
    }
}
