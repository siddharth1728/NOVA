//
//  BrowserView.swift
//  NOVA iOS Control Center
//
//  Phase 08: Deterministic Browser Automation and Remote Tab Management.
//

import SwiftUI

public struct BrowserView: View {
    @State private var status: BrowserStatusResponse?
    @State private var tabs: [BrowserTabItem] = []
    @State private var newUrl: String = ""
    @State private var isLoading: Bool = false
    @State private var isPerformingAction: Bool = false
    @State private var errorMessage: String?
    @State private var showErrorAlert: Bool = false

    public init() {}

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    // Subsystem Status Card
                    statusCard

                    // Open New Tab Section
                    openTabCard

                    // Active Tabs Section
                    activeTabsSection
                }
                .padding()
            }
            .navigationTitle("Browser")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await refreshAll() }
                    } label: {
                        if isLoading {
                            ProgressView()
                                .scaleEffect(0.8)
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                    }
                    .disabled(isLoading)
                }
            }
            .refreshable {
                await refreshAll()
            }
            .task {
                await refreshAll()
            }
            .alert("Browser Error", isPresented: $showErrorAlert) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(errorMessage ?? "An unexpected error occurred.")
            }
        }
    }

    // MARK: - Status Card

    private var statusCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("Browser Automation", systemImage: "globe")
                    .font(.headline)
                Spacer()
                if let status = status {
                    HStack(spacing: 6) {
                        Circle()
                            .fill(status.running ? Color.green : (status.enabled ? Color.yellow : Color.red))
                            .frame(width: 8, height: 8)
                        Text(status.running ? "Running" : (status.enabled ? "Ready" : "Disabled"))
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Text("Checking...")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Divider()

            HStack(spacing: 16) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Engine")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text(status?.running == true ? "Playwright Active" : "Idle")
                        .font(.caption)
                        .fontWeight(.semibold)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("Mode")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text(status?.headless == true ? "Headless" : "Headed")
                        .font(.caption)
                        .fontWeight(.semibold)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 2) {
                    Text("Active Tabs")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text("\(tabs.count)")
                        .font(.caption)
                        .fontWeight(.semibold)
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    // MARK: - Open New Tab Card

    private var openTabCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Open Tab")
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundStyle(.secondary)

            HStack(spacing: 8) {
                TextField("https://example.com", text: $newUrl)
                    .textFieldStyle(.plain)
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
                    .keyboardType(.URL)
                    .padding(10)
                    .background(Color(.tertiarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                Button {
                    Task { await openTab() }
                } label: {
                    if isPerformingAction {
                        ProgressView()
                            .tint(.white)
                            .padding(.horizontal, 14)
                            .padding(.vertical, 10)
                    } else {
                        Text("Open")
                            .fontWeight(.medium)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 10)
                    }
                }
                .buttonStyle(.borderedProminent)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .disabled(newUrl.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isPerformingAction)
            }

            // Quick presets
            HStack(spacing: 8) {
                presetButton(title: "Google", url: "https://www.google.com")
                presetButton(title: "GitHub", url: "https://github.com")
                presetButton(title: "Hacker News", url: "https://news.ycombinator.com")
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func presetButton(title: String, url: String) -> some View {
        Button {
            newUrl = url
        } label: {
            Text(title)
                .font(.caption2)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color(.tertiarySystemBackground))
                .foregroundStyle(.primary)
                .clipShape(Capsule())
        }
    }

    // MARK: - Active Tabs Section

    private var activeTabsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Open Tabs")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundStyle(.secondary)
                Spacer()
                Text("\(tabs.count)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if tabs.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "globe.badge.chevron.backward")
                        .font(.system(size: 32))
                        .foregroundStyle(.secondary)
                    Text("No Tabs Open")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text("Enter a URL above to launch a page in the Windows browser.")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 32)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12))
            } else {
                VStack(spacing: 8) {
                    ForEach(tabs) { tab in
                        tabRow(tab: tab)
                    }
                }
            }
        }
    }

    private func tabRow(tab: BrowserTabItem) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 6) {
                        Text(tab.title.isEmpty ? "Untitled Tab" : tab.title)
                            .font(.subheadline)
                            .fontWeight(.semibold)
                            .lineLimit(1)

                        if tab.isActive {
                            Text("ACTIVE")
                                .font(.system(size: 9, weight: .bold))
                                .padding(.horizontal, 5)
                                .padding(.vertical, 2)
                                .background(Color.blue.opacity(0.15))
                                .foregroundStyle(Color.blue)
                                .clipShape(Capsule())
                        }
                    }

                    Text(tab.url.isEmpty ? "about:blank" : tab.url)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                Spacer()

                HStack(spacing: 8) {
                    Button {
                        Task { await focusTab(tabId: tab.tabId) }
                    } label: {
                        Image(systemName: "macwindow.on.rectangle")
                            .font(.caption)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)

                    Button(role: .destructive) {
                        Task { await closeTab(tabId: tab.tabId) }
                    } label: {
                        Image(systemName: "xmark")
                            .font(.caption)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
            }
        }
        .padding(12)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    // MARK: - Actions

    private func refreshAll() async {
        isLoading = true
        defer { isLoading = false }
        do {
            async let fetchedStatus = NovaClient.shared.getBrowserStatus()
            async let fetchedTabs = NovaClient.shared.listBrowserTabs()
            let (s, t) = try await (fetchedStatus, fetchedTabs)
            self.status = s
            self.tabs = t
        } catch {
            self.errorMessage = error.localizedDescription
            self.showErrorAlert = true
        }
    }

    private func openTab() async {
        let trimmed = newUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        isPerformingAction = true
        defer { isPerformingAction = false }
        do {
            _ = try await NovaClient.shared.createBrowserTab(url: trimmed)
            newUrl = ""
            await refreshAll()
        } catch {
            self.errorMessage = error.localizedDescription
            self.showErrorAlert = true
        }
    }

    private func focusTab(tabId: String) async {
        do {
            _ = try await NovaClient.shared.focusBrowserTab(tabId: tabId)
            await refreshAll()
        } catch {
            self.errorMessage = error.localizedDescription
            self.showErrorAlert = true
        }
    }

    private func closeTab(tabId: String) async {
        do {
            _ = try await NovaClient.shared.closeBrowserTab(tabId: tabId)
            await refreshAll()
        } catch {
            self.errorMessage = error.localizedDescription
            self.showErrorAlert = true
        }
    }
}
