//
//  Pokemon.swift
//  WorldDex
//
//  Created by Anthony Qin on 10/27/23.
//

import SwiftUI

struct ImageResponse: Decodable {
    let imagePaths: [Pokemon]
}

struct Pokemon: Identifiable, Decodable, Equatable {
    let image_id: String // ITEM_ID
    let user_id: String
    let ipfs_cid: String
    let date_added: String // TIME
    let location_taken: String
    var cropped_image_url: String
    var image_url: String
    let details: String // live observations
    let image_classification: String
    let probability: String
    
    // Computed property for Identifiable conformance
    var id: String { image_id }
}
