//
//  TaskExecutionView.swift
//  NOVA iOS Control Center
//
//  Phase 09: Native multi-step agentic task execution monitor, approval gates, and step progress.
//

import SwiftUI

public struct TaskExecutionView: View {
    @ObservedObject private var appModel = NovaAppModel.shared
    @State private var task: TaskDetailResponse?
    @State private var steps: [TaskStepResponse] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var isRefreshing = false

    private let taskId: String

    public init(taskId: String) {
        self.taskId = taskId
    }

    public var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                if let err = errorMessage {
                    errorBanner(err)
                }

                if let currentTask = task {
                    headerCard(currentTask)

                    // Approval Required Callout
                    if currentTask.status == .awaitingApproval || currentTask.status == .waitingForApproval {
                        approvalCard(currentTask)
                    }

                    // Progress Overview Card
                    progressCard(currentTask)

                    // Execution Controls
                    controlsSection(currentTask)

                    // Multi-Step Timeline
                    stepsTimelineSection

                    // Task Result Card
                    if currentTask.status == .completed, let summary = currentTask.responseText {
                        completionCard(summary: summary, duration: currentTask.durationSeconds)
                    }
                } else if isLoading {
                    HStack {
                        Spacer()
                        ProgressView("Loading task...")
                        Spacer()
                    }
                    .padding(.top, 40)
                }
            }
            .padding()
        }
        .navigationTitle("Task Execution")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task { await refreshTask() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .disabled(isRefreshing)
            }
        }
        .task {
            await refreshTask()
        }
    }

    // =========================================================================
    // UI Components
    // =========================================================================

    private func headerCard(_ t: TaskDetailResponse) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("TASK #\(t.taskId.suffix(8))")
                    .font(.caption2.bold())
                    .foregroundStyle(.secondary)
                Spacer()
                statusBadge(t.status)
            }

            Text(t.query)
                .font(.headline)
                .foregroundStyle(.primary)

            HStack(spacing: 12) {
                Label("Risk: \(t.riskLevel)", systemImage: "shield.lefthalf.filled")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                if t.durationSeconds > 0 {
                    Label("\(String(format: "%.1f", t.durationSeconds))s", systemImage: "clock")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private func progressCard(_ t: TaskDetailResponse) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Workflow Progress")
                    .font(.subheadline.bold())
                Spacer()
                Text("\(t.completedSteps) / \(t.totalSteps) steps (\(Int(t.progressPercent))%)")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
            }

            ProgressView(value: Double(t.completedSteps), total: max(Double(t.totalSteps), 1.0))
                .tint(progressTint(t.status))

            if let curDesc = t.currentStepDescription, t.status == .executing {
                HStack(spacing: 6) {
                    ProgressView()
                        .scaleEffect(0.7)
                    Text(curDesc)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private func approvalCard(_ t: TaskDetailResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                Text("Human Approval Required")
                    .font(.subheadline.bold())
                    .foregroundStyle(.orange)
            }

            Text("This action requires verified authorization before the host agent can execute it.")
                .font(.caption)
                .foregroundStyle(.secondary)

            if let appData = t.pendingApproval {
                VStack(alignment: .leading, spacing: 4) {
                    if let tool = appData["tool"] {
                        Text("Action: \(tool)").font(.caption.bold())
                    }
                    if let target = appData["target"] {
                        Text("Target: \(target)").font(.caption2).foregroundStyle(.secondary)
                    }
                    if let reason = appData["reason"] {
                        Text("Reason: \(reason)").font(.caption2).foregroundStyle(.secondary)
                    }
                }
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.orange.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }

            HStack(spacing: 12) {
                Button {
                    Task { await submitApproval(approved: true) }
                } label: {
                    Label("Approve Action", systemImage: "checkmark.circle.fill")
                        .font(.caption.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(Color.green)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }

                Button {
                    Task { await submitApproval(approved: false) }
                } label: {
                    Label("Deny", systemImage: "xmark.circle.fill")
                        .font(.caption.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(Color.red.opacity(0.15))
                        .foregroundStyle(.red)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
        }
        .padding()
        .background(Color.orange.opacity(0.12))
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(Color.orange.opacity(0.3), lineWidth: 1)
        )
    }

    private var stepsTimelineSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Execution Steps")
                .font(.subheadline.bold())

            if steps.isEmpty {
                Text("No steps generated yet.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(steps) { step in
                    stepRow(step)
                }
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private func stepRow(_ s: TaskStepResponse) -> some View {
        HStack(alignment: .top, spacing: 12) {
            stepStatusIcon(s.status)
                .frame(width: 24)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text("Step \(s.stepId): \(s.tool)")
                        .font(.caption.bold())
                    Spacer()
                    riskBadge(s.riskLevel)
                }

                Text(s.description)
                    .font(.caption2)
                    .foregroundStyle(.secondary)

                if let err = s.error {
                    Text("Error: \(err)")
                        .font(.caption2)
                        .foregroundStyle(.red)
                }

                if s.attemptCount > 1 {
                    Text("Retries: \(s.attemptCount - 1)")
                        .font(.caption2)
                        .foregroundStyle(.orange)
                }
            }
        }
        .padding(.vertical, 4)
    }

    private func controlsSection(_ t: TaskDetailResponse) -> some View {
        HStack(spacing: 12) {
            if t.status == .executing {
                Button {
                    Task { await pauseTask() }
                } label: {
                    Label("Pause", systemImage: "pause.fill")
                        .font(.caption.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(Color(.tertiarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            } else if t.status == .paused {
                Button {
                    Task { await resumeTask() }
                } label: {
                    Label("Resume", systemImage: "play.fill")
                        .font(.caption.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(Color.blue)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }

            if t.status == .executing || t.status == .paused || t.status == .awaitingApproval {
                Button {
                    Task { await cancelTask() }
                } label: {
                    Label("Cancel Task", systemImage: "xmark.octagon.fill")
                        .font(.caption.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(Color.red.opacity(0.15))
                        .foregroundStyle(.red)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
        }
    }

    private func completionCard(summary: String, duration: Double) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Label("Verification Passed", systemImage: "checkmark.seal.fill")
                    .font(.subheadline.bold())
                    .foregroundStyle(.green)
                Spacer()
                Text("\(String(format: "%.2f", duration))s")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            Text(summary)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(Color.green.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private func stepStatusIcon(_ status: String) -> some View {
        switch status.uppercased() {
        case "COMPLETED":
            return Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
        case "RUNNING":
            return Image(systemName: "arrow.triangle.2.circlepath.circle.fill").foregroundStyle(.blue)
        case "FAILED":
            return Image(systemName: "xmark.circle.fill").foregroundStyle(.red)
        case "ROLLED_BACK":
            return Image(systemName: "arrow.uturn.backward.circle.fill").foregroundStyle(.orange)
        default:
            return Image(systemName: "circle").foregroundStyle(.secondary)
        }
    }

    private func statusBadge(_ s: TaskStatus) -> some View {
        Text(s.rawValue)
            .font(.caption2.bold())
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(statusColor(s).opacity(0.15))
            .foregroundStyle(statusColor(s))
            .clipShape(Capsule())
    }

    private func statusColor(_ s: TaskStatus) -> Color {
        switch s {
        case .completed: return .green
        case .executing, .planning, .verifying: return .blue
        case .awaitingApproval, .waitingForApproval: return .orange
        case .paused, .rolledBack: return .orange
        case .failed, .cancelled: return .red
        default: return .secondary
        }
    }

    private func progressTint(_ s: TaskStatus) -> Color {
        switch s {
        case .completed: return .green
        case .failed: return .red
        case .paused, .awaitingApproval, .waitingForApproval: return .orange
        default: return .blue
        }
    }

    private func riskBadge(_ r: String) -> some View {
        Text(r)
            .font(.system(size: 9, weight: .bold))
            .padding(.horizontal, 4)
            .padding(.vertical, 1)
            .background(Color(.tertiarySystemBackground))
            .foregroundStyle(.secondary)
            .clipShape(RoundedRectangle(cornerRadius: 4))
    }

    private func errorBanner(_ msg: String) -> some View {
        HStack {
            Image(systemName: "exclamationmark.circle.fill").foregroundStyle(.red)
            Text(msg).font(.caption).foregroundStyle(.red)
            Spacer()
        }
        .padding()
        .background(Color.red.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    // =========================================================================
    // API Actions
    // =========================================================================

    private func refreshTask() async {
        isRefreshing = true
        do {
            let client = appModel.client
            let detail = try await client.getOrchestratedTask(taskId: taskId)
            self.task = detail
            let stepList = try await client.getOrchestratedTaskSteps(taskId: taskId)
            self.steps = stepList.steps
            self.errorMessage = nil
        } catch {
            self.errorMessage = error.localizedDescription
        }
        isRefreshing = false
        isLoading = false
    }

    private func pauseTask() async {
        do {
            _ = try await appModel.client.pauseOrchestratedTask(taskId: taskId)
            await refreshTask()
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    private func resumeTask() async {
        do {
            _ = try await appModel.client.resumeOrchestratedTask(taskId: taskId)
            await refreshTask()
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    private func cancelTask() async {
        do {
            _ = try await appModel.client.cancelOrchestratedTask(taskId: taskId)
            await refreshTask()
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    private func submitApproval(approved: Bool) async {
        guard let t = task, let appData = t.pendingApproval, let sIdStr = appData["step_id"], let sId = Int(sIdStr) else { return }
        do {
            _ = try await appModel.client.approveOrchestratedTaskStep(taskId: taskId, stepId: sId, approved: approved)
            await refreshTask()
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }
}
