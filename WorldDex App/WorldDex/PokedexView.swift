//
//  PokedexView.swift
//  WorldDex
//
//  Created by Anthony Qin on 10/27/23.
//
import SwiftUI
import Combine
import SwiftyGif
import Kingfisher


struct PokemonCell: View {
    var pokemon: Pokemon
    
    var body: some View {
        NavigationLink(destination: PokemonDetailView(pokemon: pokemon)) {
            VStack {
                KFImage(URL(string: pokemon.cropped_image_url))
                    .resizable()
                    .scaledToFit()
                    .cornerRadius(15)
                    .frame(width: 150, height: 150)
            }
            .padding()
            .frame(width: 200, height: 200)
            .background(Color.gray.opacity(0.2))
            .cornerRadius(15)
        }
        .shadow(color: Color.black.opacity(0.7), radius: 15, x: 0, y: 0)
    }
}

struct PokedexView: View {
    @State private var pokemonList: [Pokemon] = []
    @State private var isLoading: Bool = true // Track loading state
    @State private var isEmpty: Bool = true
    var userId: String = UserDefaults.standard.string(forKey: "username") ?? ""

    func fetchPokemon() {
        // Assuming Constants and Endpoints are correctly set up
        let url = URL(string: Constants.baseURL + Constants.Endpoints.userImages + "?user_id=\(userId)&page=1")!

        URLSession.shared.dataTask(with: url) { data, response, error in
            if let data = data {
                do {
                    let fetchedData = try JSONDecoder().decode([String: [Pokemon]].self, from: data)
                    if let fetchedPokemons = fetchedData["images"] {
                        let sortedPokemons = fetchedPokemons.sorted(by: {
                            $0.date_added > $1.date_added
                        })
                        DispatchQueue.main.async {
                            self.pokemonList = sortedPokemons
                            self.isEmpty = false
                            self.isLoading = false

                            // Prefetch images after sorting
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
                            self.fetchPokemon()
                        }
                    if isLoading {
                        GifImageView(gifName: "loading", desiredWidth: 50, desiredHeight: 50)
                            .frame(width: 50, height: 50)
                    }
                }
            } else {
                NavigationView {
                    Group {
                        ScrollView {
                            LazyVGrid(columns: [GridItem(.fixed(197), spacing: 10),
                                                GridItem(.fixed(197), spacing: 10)]) {
                                ForEach(pokemonList, id: \.id) { pokemon in
                                    PokemonCell(pokemon: pokemon)
                                }
                            }.padding()
                        }
                        .background(Color("theme1"))
                    }
                    .navigationTitle("WorldDex")
                    .background(Color("theme1").edgesIgnoringSafeArea(.all))
                }
            }
        }
    }
}


