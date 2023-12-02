//
//  PokemonPostView.swift
//  WorldDex
//
//  Created by Anthony Qin on 10/27/23.
//

import SwiftUI

struct PokemonPostView: View {
    let pokemon: Pokemon

    var body: some View {
        VStack(alignment: .leading, spacing: 15) {
            HStack {
                VStack(alignment: .leading) {
                    Text(pokemon.user_id)
                        .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .headline).pointSize))
                        .foregroundColor(.black)
                        .bold()
                    Text(pokemon.location_taken)
                        .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .subheadline).pointSize))
                        .foregroundColor(.black)
                }
                Spacer()
                Text(formattedDate)
                    .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .subheadline).pointSize))
                    .foregroundColor(.black)
            }
            
            HStack {
                Spacer()
                Image(uiImage: pokemonImage(from: pokemon.image))
                    .resizable()
                    .scaledToFit()
                    .frame(height: 200)
                Image(uiImage: pokemonImage(from: pokemon.cropped_image))
                    .resizable()
                    .scaledToFit()
                    .frame(height: 200)
                Spacer()
            }
            
            Text(pokemon.image_classification.split(separator: "_").first ?? "")
                .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .title2).pointSize))
                .foregroundColor(.black)
                .bold()
            
            Text(captureText)
                .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .subheadline).pointSize))
                .foregroundColor(.black)
                .italic()
            
            Text(pokemon.details)
                .font(Font.custom("Avenir", size: UIFont.preferredFont(forTextStyle: .body).pointSize))
                .foregroundColor(.black)
            
            Divider()
        }
        .padding()
    }
    
    var formattedDate: String {
        let inputFormatter = DateFormatter()
        inputFormatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS" // Updated to match your timestamp format
        inputFormatter.locale = Locale(identifier: "en_US_POSIX") // Added to handle locale-specific behaviors

        let outputFormatter = DateFormatter()
        outputFormatter.dateFormat = "MM/dd/yyyy hh:mm:ss a"
        outputFormatter.amSymbol = "AM" // Explicitly set AM symbol
        outputFormatter.pmSymbol = "PM" // Explicitly set PM symbol
        outputFormatter.locale = Locale(identifier: "en_US_POSIX") // Ensure consistent 12-hour format

        if let date = inputFormatter.date(from: pokemon.date_added) {
            return outputFormatter.string(from: date)
        }
        return pokemon.date_added
    }

    
    var captureText: String {
        let id = pokemon.user_id
        let chance = String(pokemon.probability.prefix(4))
        let item = pokemon.image_classification.split(separator: "_").first ?? ""
        return "\(id) had a \(chance)% chance of capturing this \(item)!"
    }
    
    func pokemonImage(from base64: String) -> UIImage {
        guard let data = Data(base64Encoded: base64), let image = UIImage(data: data) else {
            return UIImage() // or a default image if desired
        }
        return image
    }
}
