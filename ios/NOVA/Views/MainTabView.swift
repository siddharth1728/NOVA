//
//  MainTabView.swift
//  NOVA iOS Control Center
//
//  Authoritative 5-tab primary navigation structure for iPhone.
//

import SwiftUI

public struct MainTabView: View {
    @State private var selectedTab = 0

    public init() {}

    public var body: some View {
        TabView(selection: $selectedTab) {
            HomeView()
                .tabItem {
                    Label("Home", systemImage: "house.fill")
                }
                .tag(0)

            AgentView()
                .tabItem {
                    Label("Agent", systemImage: "brain.head.profile")
                }
                .tag(1)

            ComputerView()
                .tabItem {
                    Label("Computer", systemImage: "display")
                }
                .tag(2)

            ActivityView()
                .tabItem {
                    Label("Activity", systemImage: "waveform.path.ecg")
                }
                .tag(3)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape.fill")
                }
                .tag(4)
        }
    }
}
