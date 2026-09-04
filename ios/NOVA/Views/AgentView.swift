//
//  AgentView.swift
//  NOVA iOS Control Center
//
//  Interactive natural language query dispatch, execution progress, and verified result inspection.
//

import SwiftUI

public struct AgentView: View {
    @State private var queryText = ""
    @State private var isExecuting = false
    @State private var lastResponse: RemoteQueryResponse?
    @State private var errorMessage: String?
    @State private var executionHistory: [RemoteQueryResponse] = []

    public init() {}

    public var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        // Quick Prompt Suggestions
                        suggestionsSection

                        if let err = errorMessage {
                            errorBanner(err)
                        }

                        if isExecuting {
                            executingCard
                        }

                        // Last Execution Result
                        if let resp = lastResponse {
                            responseCard(resp)
                        }

                        // History
                        if !executionHistory.isEmpty {
                            historySection
                        }
                    }
                    .padding()
                }

                // Bottom Query Input Bar
                queryInputBar
            }
            .navigationTitle("Agent Runtime")
        }
    }

    private var suggestionsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Suggested Tasks")
                .font(.caption)
                .foregroundStyle(.secondary)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    suggestionChip("List workspace files")
                    suggestionChip("Inspect project structure")
                    suggestionChip("Verify git branch status")
                }
            }
        }
    }

    private func suggestionChip(_ prompt: String) -> some View {
        Button(prompt) {
            queryText = prompt
        }
        .font(.caption)
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Color(.secondarySystemBackground))
        .clipShape(Capsule())
    }

    private var executingCard: some View {
        HStack(spacing: 12) {
            ProgressView()
            VStack(alignment: .leading, spacing: 2) {
                Text("Executing on Windows PC...")
                    .font(.subheadline.bold())
                Text("Running through Antigravity safety policies & audit...")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.blue.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func responseCard(_ resp: RemoteQueryResponse) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("Task Verified", systemImage: "checkmark.seal.fill")
                    .font(.subheadline.bold())
                    .foregroundStyle(.green)
                Spacer()
                Text(resp.status)
                    .font(.caption2.bold())
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.green.opacity(0.2))
                    .foregroundStyle(.green)
                    .clipShape(Capsule())
            }

            Text("Goal: \(resp.query)")
                .font(.caption)
                .foregroundStyle(.secondary)

            Divider()

            Text(resp.responseText)
                .font(.system(.footnote, design: .monospaced))
                .textSelection(.enabled)
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(.tertiarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 8))

            HStack {
                Text("Session ID: \(resp.sessionId.prefix(8))")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Spacer()
                Button {
                    UIPasteboard.general.string = resp.responseText
                } label: {
                    Label("Copy Result", systemImage: "doc.on.doc")
                        .font(.caption2)
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var historySection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Recent Executions")
                .font(.headline)

            ForEach(executionHistory, id: \.sessionId) { item in
                VStack(alignment: .leading, spacing: 4) {
                    Text(item.query)
                        .font(.caption.bold())
                    Text(item.responseText.prefix(80) + "...")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 10))
            }
        }
    }

    private var queryInputBar: some View {
        HStack(spacing: 8) {
            TextField("Ask NOVA or dispatch task...", text: $queryText)
                .padding(10)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 20))
                .disabled(isExecuting)

            Button {
                Task { await submitQuery() }
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(queryText.trimmingCharacters(in: .whitespaces).isEmpty ? .gray : .blue)
            }
            .disabled(queryText.trimmingCharacters(in: .whitespaces).isEmpty || isExecuting)
        }
        .padding()
        .background(Color(.systemBackground))
        .overlay(Divider(), alignment: .top)
    }

    private func errorBanner(_ msg: String) -> some View {
        HStack {
            Image(systemName: "exclamationmark.circle.fill")
                .foregroundStyle(.red)
            Text(msg)
                .font(.caption)
                .foregroundStyle(.red)
            Spacer()
        }
        .padding()
        .background(Color.red.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private func submitQuery() async {
        let prompt = queryText.trimmingCharacters(in: .whitespaces)
        guard !prompt.isEmpty else { return }

        queryText = ""
        isExecuting = true
        errorMessage = nil

        do {
            let resp = try await NovaClient.shared.sendAgentQuery(prompt: prompt)
            self.lastResponse = resp
            self.executionHistory.insert(resp, at: 0)
        } catch {
            self.errorMessage = error.localizedDescription
        }

        isExecuting = false
    }
}
