//
//  SocialPageView.swift
//  WorldDex
//
//  Created by Anthony Qin on 10/27/23.
//

import SwiftUI
import SwiftyGif
import Kingfisher

struct SocialPageView: View {
    @State private var friendsPokemons: [Pokemon] = []
    var userId: String = UserDefaults.standard.string(forKey: "username") ?? ""
    @State private var isLoading: Bool = true
    @State private var isEmpty: Bool = true
    
    func fetchFriendsPokemon() {
        let url = URL(string: Constants.baseURL + Constants.Endpoints.excludeUserImages + "?user_id=\(userId)&page=1")!

        URLSession.shared.dataTask(with: url) { data, response, error in
            if let data = data {
                do {
                    let fetchedData = try JSONDecoder().decode([String: [Pokemon]].self, from: data)
                    if let fetchedPokemons = fetchedData["images"] {
                        let sortedPokemons = fetchedPokemons.sorted(by: {
                            $0.date_added > $1.date_added
                        })
                        DispatchQueue.main.async {
                            self.friendsPokemons = sortedPokemons
                            self.isLoading = false
                            self.isEmpty = false
                            self.prefetchImages(pokemons: sortedPokemons)
                        }
                    }
                } catch {
                    print("Error decoding: \(error)")
                    DispatchQueue.main.async {
                        self.isLoading = false
                        self.isEmpty = true
                    }
                }
            } else if let error = error {
                print("Error fetching data: \(error)")
                DispatchQueue.main.async {
                    self.isLoading = false
                    self.isEmpty = true
                }
            }
        }.resume()
    }

    func prefetchImages(pokemons: [Pokemon]) {
        let urls = pokemons.compactMap { URL(string: $0.image_url) }
        let prefetcher = ImagePrefetcher(urls: urls)
        prefetcher.start()
    }

    
    var body: some View {
        ZStack {
            Color("theme1").edgesIgnoringSafeArea(.all)
            if isEmpty {
                VStack {
                    Image("worldexIcon")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 100, height: 100)
                        .onAppear {
                            self.fetchFriendsPokemon()
                        }
                    if isLoading {
                        GifImageView(gifName: "loading", desiredWidth: 50, desiredHeight: 50)
                            .frame(width: 50, height: 50)
                    }
                }
            } else {
                VStack {
                    Text("Community")
                        .font(.custom("Avenir", size: 26))
                        .bold()
                        .foregroundColor(.black)
                        .padding(.top, 10)
                    ScrollView {
                        VStack(spacing: 20) {
                            ForEach(friendsPokemons, id: \.id) { pokemon in
                                PokemonPostView(pokemon: pokemon)
                            }
                        }
                        .padding(.top)
                    }
                }
                .background(Color("theme1").edgesIgnoringSafeArea(.all))
            }
        }
    }
}
