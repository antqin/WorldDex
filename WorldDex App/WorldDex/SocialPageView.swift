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
    @State private var isLastPageLoaded: Bool = false
    @State private var currentPage = 1
    @State private var nextPage = 2
    @State private var items_per_page = 3
    
    func fetchFriendsPokemon() {
        // Check if we've already loaded the last page
        guard !isLastPageLoaded else { return }

        let url = URL(string: Constants.baseURL + Constants.Endpoints.excludeUserImages + "?user_id=\(userId)&page=\(currentPage)&items_per_page=\(items_per_page)")!

        URLSession.shared.dataTask(with: url) { data, response, error in
            if let data = data {
                do {
                    let fetchedData = try JSONDecoder().decode([String: [Pokemon]].self, from: data)
                    if let fetchedPokemons = fetchedData["images"], !fetchedPokemons.isEmpty {
                        let sortedPokemons = fetchedPokemons.sorted(by: {
                            $0.date_added > $1.date_added
                        })
                        DispatchQueue.main.async {
                            // If it's the first page, replace the data; otherwise, append the new data
                            if self.currentPage == 1 {
                                self.friendsPokemons = sortedPokemons
                            } else {
                                self.friendsPokemons.append(contentsOf: sortedPokemons)
                            }
                            self.isLoading = false
                            self.isEmpty = false
                            self.prefetchImages(pokemons: sortedPokemons)
                        }
                    } else {
                        DispatchQueue.main.async {
                            // No more data to load, mark the last page as loaded
                            self.isLoading = false
                            self.isLastPageLoaded = true
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
            VStack {
                Text("Community")
                    .font(.custom("Avenir", size: 26))
                    .bold()
                    .foregroundColor(.black)
                    .padding(.top, 10)
                ScrollView {
                    LazyVStack(spacing: 20) {
                        ForEach(friendsPokemons, id: \.id) { pokemon in
                            PokemonPostView(pokemon: pokemon)
                                .onAppear {
                                    if pokemon == friendsPokemons.last && !isLoading && !isLastPageLoaded {
                                        loadMoreContent()
                                    }
                                }
                        }
                    }
                    .padding(.top)
                }
            }
            .background(Color("theme1").edgesIgnoringSafeArea(.all))
            // Loading and Empty Views here
        }
        .onAppear {
            fetchFriendsPokemon()
        }
    }
    
    func shouldLoadMoreContent(pokemon: Pokemon) -> Bool {
        // Check if the current pokemon is the last one in the list and if the next page is not the current page
        return pokemon == friendsPokemons.last && currentPage < nextPage && !isLastPageLoaded
    }

    func loadMoreContent() {
        currentPage = nextPage
        nextPage += 1
        fetchFriendsPokemon()
    }
}
